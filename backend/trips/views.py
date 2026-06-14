import json
import hashlib
import secrets
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import ApiToken, Expense, Settlement, Trip, TripMember, WechatProfile
from .services import mark_settlement, money, rebuild_splits, sync_settlements, trip_card_summary, trip_summary

User = get_user_model()


def token_hash(raw_token):
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def create_api_token(user, label='miniapp'):
    raw_token = secrets.token_urlsafe(32)
    ApiToken.objects.create(user=user, key_hash=token_hash(raw_token), label=label)
    return raw_token


def user_from_bearer_token(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    raw_token = auth_header.removeprefix('Bearer ').strip()
    if not raw_token:
        return None
    token = ApiToken.objects.select_related('user').filter(key_hash=token_hash(raw_token)).first()
    if token is None:
        return None
    token.last_used_at = timezone.now()
    token.save(update_fields=['last_used_at'])
    return token.user


def api_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        token_user = user_from_bearer_token(request)
        if token_user is None:
            return error('请先登录', 401)
        request.user = token_user
        return view_func(request, *args, **kwargs)

    return wrapper


def parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        raise ValueError('请求体不是有效 JSON')


def ok(data=None, status=200):
    return JsonResponse({'ok': True, **(data or {})}, status=status)


def error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def amount_from(value):
    try:
        amount = money(Decimal(str(value)))
    except (InvalidOperation, TypeError):
        raise ValueError('金额格式不正确')
    if amount <= 0:
        raise ValueError('金额必须大于 0')
    return amount


def date_from(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('日期格式必须是 YYYY-MM-DD')


def validate_date_range(start_date, end_date):
    if start_date and end_date and end_date < start_date:
        raise ValueError('结束日期不能早于开始日期')


def user_payload(user):
    return {'id': user.id, 'username': user.username}


def fetch_wechat_session(code):
    mock_prefix = getattr(settings, 'WECHAT_LOGIN_MOCK_PREFIX', 'mock:')
    if settings.DEBUG and code.startswith(mock_prefix):
        openid = code.removeprefix(mock_prefix).strip()
        if not openid:
            raise ValueError('微信 code 不正确')
        return {'openid': f'dev_{openid}', 'session_key': ''}

    appid = getattr(settings, 'WECHAT_APPID', '')
    secret = getattr(settings, 'WECHAT_APPSECRET', '')
    if not appid or not secret:
        raise ValueError('未配置微信 APPID/APPSECRET')

    params = urllib.parse.urlencode(
        {
            'appid': appid,
            'secret': secret,
            'js_code': code,
            'grant_type': 'authorization_code',
        }
    )
    url = f'https://api.weixin.qq.com/sns/jscode2session?{params}'
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except OSError:
        raise ValueError('微信登录服务暂不可用')

    if payload.get('errcode'):
        raise ValueError(payload.get('errmsg') or '微信登录失败')
    if not payload.get('openid'):
        raise ValueError('微信登录未返回 openid')
    return payload


def get_or_create_wechat_user(openid, session_key=''):
    profile = WechatProfile.objects.select_related('user').filter(openid=openid).first()
    if profile:
        if session_key and profile.session_key != session_key:
            profile.session_key = session_key
            profile.save(update_fields=['session_key', 'updated_at'])
        return profile.user

    base_username = f'wx_{openid[-16:]}'
    username = base_username[:150]
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base_username[:140]}_{suffix}'[:150]

    with transaction.atomic():
        user = User.objects.create_user(username=username, password=secrets.token_urlsafe(24))
        WechatProfile.objects.create(user=user, openid=openid, session_key=session_key or '')
    return user


def member_payload(member):
    return {
        'id': member.id,
        'display_name': member.display_name,
        'user_id': member.user_id,
        'username': member.user.username if member.user_id else '',
    }


def trip_payload(trip):
    card_summary = trip_card_summary(trip)
    return {
        'id': trip.id,
        'title': trip.title,
        'location': trip.location,
        'start_date': trip.start_date.isoformat() if trip.start_date else '',
        'end_date': trip.end_date.isoformat() if trip.end_date else '',
        'currency': trip.currency,
        'note': trip.note,
        'owner_id': trip.owner_id,
        'owner_username': trip.owner.username,
        'created_at': trip.created_at.isoformat(),
        'updated_at': trip.updated_at.isoformat(),
        'member_count': trip.members.count(),
        'expense_count': trip.expenses.count(),
        'total_amount': str(card_summary['total_amount']),
        'bill_count': card_summary['bill_count'],
        'status': card_summary['status'],
        'last_updated_at': card_summary['last_updated_at'].isoformat() if card_summary['last_updated_at'] else '',
    }


def expense_payload(expense):
    return {
        'id': expense.id,
        'trip_id': expense.trip_id,
        'payer_id': expense.payer_id,
        'payer_name': expense.payer.display_name,
        'amount': str(money(expense.amount)),
        'category': expense.category,
        'spent_at': expense.spent_at.isoformat(),
        'description': expense.description,
        'created_by_id': expense.created_by_id,
        'splits': [
            {
                'member_id': split.member_id,
                'display_name': split.member.display_name,
                'amount': str(money(split.amount)),
            }
            for split in expense.splits.select_related('member').all()
        ],
    }


def settlement_payload(settlement):
    return {
        'id': settlement.id,
        'from_member_id': settlement.from_member_id,
        'from_member_name': settlement.from_member.display_name,
        'to_member_id': settlement.to_member_id,
        'to_member_name': settlement.to_member.display_name,
        'amount': str(money(settlement.amount)),
        'is_paid': settlement.is_paid,
        'paid_at': settlement.paid_at.isoformat() if settlement.paid_at else '',
    }


def user_can_access_trip(user, trip):
    return trip.owner_id == user.id or trip.members.filter(user=user).exists()


def get_trip_for_user(user, trip_id):
    try:
        trip = (
            Trip.objects.select_related('owner')
            .prefetch_related('members', 'expenses', 'settlements')
            .get(id=trip_id)
        )
    except Trip.DoesNotExist:
        return None
    if not user_can_access_trip(user, trip):
        return None
    return trip


def owner_required(user, trip):
    if trip.owner_id != user.id:
        raise PermissionError('只有出游创建者可以修改')


@csrf_exempt
def register_view(request):
    if request.method != 'POST':
        return error('只支持 POST', 405)
    try:
        body = parse_body(request)
        username = (body.get('username') or '').strip()
        password = body.get('password') or ''
        if not username or not password:
            return error('用户名和密码不能为空')
        if User.objects.filter(username=username).exists():
            return error('用户名已存在')
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return ok({'user': user_payload(user)}, status=201)
    except ValueError as exc:
        return error(str(exc))


@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return error('只支持 POST', 405)
    try:
        body = parse_body(request)
        user = authenticate(request, username=(body.get('username') or '').strip(), password=body.get('password') or '')
        if user is None:
            return error('用户名或密码不正确', 401)
        login(request, user)
        return ok({'user': user_payload(user)})
    except ValueError as exc:
        return error(str(exc))


@csrf_exempt
def wechat_login_view(request):
    if request.method != 'POST':
        return error('只支持 POST', 405)
    try:
        body = parse_body(request)
        code = (body.get('code') or '').strip()
        if not code:
            return error('微信 code 不能为空')
        session = fetch_wechat_session(code)
        user = get_or_create_wechat_user(session['openid'], session.get('session_key', ''))
        token = create_api_token(user)
        return ok({'user': user_payload(user), 'token': token})
    except ValueError as exc:
        return error(str(exc))


@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return error('只支持 POST', 405)
    logout(request)
    return ok()


def me_view(request):
    if request.user.is_authenticated:
        return ok({'authenticated': True, 'user': user_payload(request.user)})
    return ok({'authenticated': False, 'user': None})


@csrf_exempt
@api_login_required
def trips_view(request):
    if request.method == 'GET':
        trips = (
            Trip.objects.filter(Q(owner=request.user) | Q(members__user=request.user))
            .distinct()
            .select_related('owner')
            .prefetch_related('members', 'expenses', 'settlements')
        )
        return ok({'trips': [trip_payload(trip) for trip in trips]})

    if request.method == 'POST':
        try:
            body = parse_body(request)
            title = (body.get('title') or '').strip()
            if not title:
                return error('出游名称不能为空')
            start_date = date_from(body.get('start_date'))
            end_date = date_from(body.get('end_date'))
            validate_date_range(start_date, end_date)
            trip = Trip.objects.create(
                owner=request.user,
                title=title,
                location=(body.get('location') or '').strip(),
                start_date=start_date,
                end_date=end_date,
                currency=(body.get('currency') or 'CNY').strip() or 'CNY',
                note=(body.get('note') or '').strip(),
            )
            TripMember.objects.create(trip=trip, user=request.user, display_name=request.user.username)
            return ok({'trip': trip_payload(trip)}, status=201)
        except ValueError as exc:
            return error(str(exc))

    return error('方法不支持', 405)


@csrf_exempt
@api_login_required
def trip_detail_view(request, trip_id):
    trip = get_trip_for_user(request.user, trip_id)
    if trip is None:
        return error('出游不存在或无权访问', 404)

    if request.method == 'GET':
        return ok({'trip': trip_payload(trip)})

    try:
        owner_required(request.user, trip)
        if request.method == 'PATCH':
            body = parse_body(request)
            for field in ['title', 'location', 'currency', 'note']:
                if field in body:
                    setattr(trip, field, (body.get(field) or '').strip())
            if 'start_date' in body:
                trip.start_date = date_from(body.get('start_date'))
            if 'end_date' in body:
                trip.end_date = date_from(body.get('end_date'))
            if not trip.title:
                return error('出游名称不能为空')
            validate_date_range(trip.start_date, trip.end_date)
            trip.save()
            return ok({'trip': trip_payload(trip)})

        if request.method == 'DELETE':
            with transaction.atomic():
                Expense.objects.filter(trip=trip).delete()
                trip.delete()
            return ok()
    except PermissionError as exc:
        return error(str(exc), 403)
    except ValueError as exc:
        return error(str(exc))

    return error('方法不支持', 405)


@csrf_exempt
@api_login_required
def members_view(request, trip_id):
    trip = get_trip_for_user(request.user, trip_id)
    if trip is None:
        return error('出游不存在或无权访问', 404)

    if request.method == 'GET':
        return ok({'members': [member_payload(member) for member in trip.members.select_related('user')]})

    if request.method == 'POST':
        try:
            owner_required(request.user, trip)
            body = parse_body(request)
            username = (body.get('username') or '').strip()
            linked_user = User.objects.filter(username=username).first() if username else None
            display_name = (body.get('display_name') or '').strip() or (linked_user.username if linked_user else '')
            if not display_name:
                return error('成员昵称不能为空')
            try:
                member = TripMember.objects.create(trip=trip, user=linked_user, display_name=display_name)
            except IntegrityError:
                return error('该成员已存在')
            return ok({'member': member_payload(member)}, status=201)
        except PermissionError as exc:
            return error(str(exc), 403)
        except ValueError as exc:
            return error(str(exc))

    return error('方法不支持', 405)


@csrf_exempt
@api_login_required
def member_detail_view(request, member_id):
    try:
        member = TripMember.objects.select_related('trip').get(id=member_id)
    except TripMember.DoesNotExist:
        return error('成员不存在', 404)
    if not user_can_access_trip(request.user, member.trip):
        return error('无权访问', 404)
    if request.method != 'DELETE':
        return error('方法不支持', 405)

    try:
        owner_required(request.user, member.trip)
        if member.user_id == member.trip.owner_id:
            return error('不能删除出游创建者成员')
        if member.paid_expenses.exists() or member.expense_splits.exists():
            return error('该成员已有账单关联，不能删除')
        member.delete()
        return ok()
    except PermissionError as exc:
        return error(str(exc), 403)


@csrf_exempt
@api_login_required
def expenses_view(request, trip_id):
    trip = get_trip_for_user(request.user, trip_id)
    if trip is None:
        return error('出游不存在或无权访问', 404)

    if request.method == 'GET':
        expenses = trip.expenses.select_related('payer').prefetch_related('splits__member')
        return ok({'expenses': [expense_payload(expense) for expense in expenses]})

    if request.method == 'POST':
        try:
            owner_required(request.user, trip)
            body = parse_body(request)
            try:
                payer = trip.members.get(id=body.get('payer_id'))
            except TripMember.DoesNotExist:
                return error('付款人不存在')
            split_member_ids = (
                body.get('split_member_ids')
                if 'split_member_ids' in body
                else list(trip.members.values_list('id', flat=True))
            )
            with transaction.atomic():
                expense = Expense.objects.create(
                    trip=trip,
                    payer=payer,
                    amount=amount_from(body.get('amount')),
                    category=(body.get('category') or '其他').strip() or '其他',
                    spent_at=date_from(body.get('spent_at')) or date.today(),
                    description=(body.get('description') or '').strip(),
                    created_by=request.user,
                )
                rebuild_splits(expense, split_member_ids)
            return ok({'expense': expense_payload(expense)}, status=201)
        except PermissionError as exc:
            return error(str(exc), 403)
        except ValueError as exc:
            return error(str(exc))

    return error('方法不支持', 405)


@csrf_exempt
@api_login_required
def expense_detail_view(request, expense_id):
    try:
        expense = Expense.objects.select_related('trip', 'payer').get(id=expense_id)
    except Expense.DoesNotExist:
        return error('账单不存在', 404)
    if not user_can_access_trip(request.user, expense.trip):
        return error('无权访问', 404)

    try:
        owner_required(request.user, expense.trip)
        if request.method == 'DELETE':
            expense.delete()
            return ok()

        if request.method == 'PATCH':
            body = parse_body(request)
            should_rebuild_splits = False
            if 'payer_id' in body:
                try:
                    expense.payer = expense.trip.members.get(id=body.get('payer_id'))
                except TripMember.DoesNotExist:
                    return error('付款人不存在')
            if 'amount' in body:
                expense.amount = amount_from(body.get('amount'))
                should_rebuild_splits = True
            if 'category' in body:
                expense.category = (body.get('category') or '其他').strip() or '其他'
            if 'spent_at' in body:
                expense.spent_at = date_from(body.get('spent_at')) or date.today()
            if 'description' in body:
                expense.description = (body.get('description') or '').strip()
            with transaction.atomic():
                expense.save()
                if 'split_member_ids' in body:
                    rebuild_splits(expense, body.get('split_member_ids') or [])
                elif should_rebuild_splits:
                    existing_member_ids = expense.splits.values_list('member_id', flat=True)
                    rebuild_splits(expense, existing_member_ids)
            return ok({'expense': expense_payload(expense)})
    except PermissionError as exc:
        return error(str(exc), 403)
    except ValueError as exc:
        return error(str(exc))

    return error('方法不支持', 405)


@api_login_required
def summary_view(request, trip_id):
    trip = get_trip_for_user(request.user, trip_id)
    if trip is None:
        return error('出游不存在或无权访问', 404)
    if request.method != 'GET':
        return error('方法不支持', 405)
    summary = trip_summary(trip)
    return ok(
        {
            'summary': {
                'total': str(summary['total']),
                'per_person': str(summary['per_person']),
                'members': [
                    {
                        **row,
                        'paid': str(row['paid']),
                        'share': str(row['share']),
                        'net': str(row['net']),
                    }
                    for row in summary['members']
                ],
            }
        }
    )


@csrf_exempt
@api_login_required
def settlements_view(request, trip_id):
    trip = get_trip_for_user(request.user, trip_id)
    if trip is None:
        return error('出游不存在或无权访问', 404)
    if request.method != 'GET':
        return error('方法不支持', 405)
    records = sync_settlements(trip)
    return ok({'settlements': [settlement_payload(item) for item in records]})


@csrf_exempt
@api_login_required
def settlement_detail_view(request, settlement_id):
    try:
        settlement = Settlement.objects.select_related('trip', 'from_member', 'to_member').get(id=settlement_id)
    except Settlement.DoesNotExist:
        return error('结算记录不存在', 404)
    if not user_can_access_trip(request.user, settlement.trip):
        return error('无权访问', 404)
    if request.method != 'PATCH':
        return error('方法不支持', 405)
    try:
        owner_required(request.user, settlement.trip)
        body = parse_body(request)
        settlement = mark_settlement(settlement, body.get('is_paid', True))
        return ok({'settlement': settlement_payload(settlement)})
    except PermissionError as exc:
        return error(str(exc), 403)
    except ValueError as exc:
        return error(str(exc))
