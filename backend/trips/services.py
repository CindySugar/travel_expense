from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.utils import timezone

from .models import ExpenseSplit, Settlement, TripMember

CENT = Decimal('0.01')


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def split_evenly(amount, member_count):
    if member_count <= 0:
        raise ValueError('至少选择一个分摊成员')
    amount = money(amount)
    base = (amount / Decimal(member_count)).quantize(CENT, rounding=ROUND_HALF_UP)
    values = [base for _ in range(member_count)]
    remainder = amount - sum(values, Decimal('0.00'))
    values[-1] = money(values[-1] + remainder)
    return values


def rebuild_splits(expense, member_ids):
    try:
        normalized_ids = [int(member_id) for member_id in member_ids]
    except (TypeError, ValueError):
        raise ValueError('分摊成员格式不正确')
    if not normalized_ids:
        raise ValueError('至少选择一个分摊成员')
    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError('分摊成员不能重复')

    members = list(TripMember.objects.filter(trip=expense.trip, id__in=normalized_ids).order_by('id'))
    found_ids = {member.id for member in members}
    missing_ids = sorted(set(normalized_ids) - found_ids)
    if missing_ids:
        raise ValueError('分摊成员不存在或不属于该出游')

    ExpenseSplit.objects.filter(expense=expense).delete()
    amounts = split_evenly(expense.amount, len(members))
    ExpenseSplit.objects.bulk_create(
        ExpenseSplit(expense=expense, member=member, amount=amount)
        for member, amount in zip(members, amounts)
    )


def trip_summary(trip):
    members = list(trip.members.all())
    paid_by_member = {
        item['payer_id']: money(item['total'])
        for item in trip.expenses.values('payer_id').annotate(total=Sum('amount'))
    }
    share_by_member = {
        item['member_id']: money(item['total'])
        for item in ExpenseSplit.objects.filter(expense__trip=trip)
        .values('member_id')
        .annotate(total=Sum('amount'))
    }
    total = money(trip.expenses.aggregate(total=Sum('amount'))['total'])

    rows = []
    for member in members:
        paid = paid_by_member.get(member.id, Decimal('0.00'))
        share = share_by_member.get(member.id, Decimal('0.00'))
        net = money(paid - share)
        rows.append(
            {
                'member_id': member.id,
                'display_name': member.display_name,
                'paid': paid,
                'share': share,
                'net': net,
                'direction': 'receivable' if net > 0 else 'payable' if net < 0 else 'settled',
            }
        )

    per_person = money(total / Decimal(len(members))) if members else Decimal('0.00')
    return {'total': total, 'per_person': per_person, 'members': rows}


def settlement_suggestions(trip):
    summary = trip_summary(trip)
    debtors = [
        {'member_id': row['member_id'], 'display_name': row['display_name'], 'amount': money(-row['net'])}
        for row in summary['members']
        if row['net'] < 0
    ]
    creditors = [
        {'member_id': row['member_id'], 'display_name': row['display_name'], 'amount': money(row['net'])}
        for row in summary['members']
        if row['net'] > 0
    ]
    debtors.sort(key=lambda item: item['amount'], reverse=True)
    creditors.sort(key=lambda item: item['amount'], reverse=True)

    suggestions = []
    debtor_index = 0
    creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]
        amount = min(debtor['amount'], creditor['amount'])
        if amount > 0:
            suggestions.append(
                {
                    'from_member_id': debtor['member_id'],
                    'from_member_name': debtor['display_name'],
                    'to_member_id': creditor['member_id'],
                    'to_member_name': creditor['display_name'],
                    'amount': money(amount),
                }
            )
        debtor['amount'] = money(debtor['amount'] - amount)
        creditor['amount'] = money(creditor['amount'] - amount)
        if debtor['amount'] == 0:
            debtor_index += 1
        if creditor['amount'] == 0:
            creditor_index += 1
    return suggestions


def sync_settlements(trip):
    suggestions = settlement_suggestions(trip)
    paid_records = {
        (item.from_member_id, item.to_member_id, money(item.amount)): item
        for item in trip.settlements.filter(is_paid=True)
    }
    trip.settlements.filter(is_paid=False).delete()

    records = []
    for suggestion in suggestions:
        key = (suggestion['from_member_id'], suggestion['to_member_id'], money(suggestion['amount']))
        paid = paid_records.get(key)
        if paid:
            records.append(paid)
        else:
            records.append(
                Settlement.objects.create(
                    trip=trip,
                    from_member_id=suggestion['from_member_id'],
                    to_member_id=suggestion['to_member_id'],
                    amount=suggestion['amount'],
                )
            )
    return records


def mark_settlement(settlement, is_paid):
    settlement.is_paid = bool(is_paid)
    settlement.paid_at = timezone.now() if settlement.is_paid else None
    settlement.save(update_fields=['is_paid', 'paid_at'])
    return settlement
