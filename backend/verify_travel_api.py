import json
import os
import uuid
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
from django.contrib.auth import get_user_model
from django.test import Client

django.setup()

from trips.models import Expense, Trip

User = get_user_model()


def assert_status(response, expected_status, label):
    if response.status_code != expected_status:
        raise AssertionError(f"{label}: expected {expected_status}, got {response.status_code}, body={response.content!r}")
    return response.json()


def post_json(client, path, payload):
    return client.post(path, data=json.dumps(payload), content_type="application/json")


def patch_json(client, path, payload):
    return client.patch(path, data=json.dumps(payload), content_type="application/json")


def bearer_client(token):
    return Client(HTTP_HOST="127.0.0.1", HTTP_AUTHORIZATION=f"Bearer {token}")


def register(client, username, password="pass12345"):
    return assert_status(post_json(client, "/api/auth/register/", {"username": username, "password": password}), 201, "register")


def main():
    suffix = uuid.uuid4().hex[:8]
    owner_username = f"alice_{suffix}"
    stranger_username = f"mallory_{suffix}"
    owner = Client(HTTP_HOST="127.0.0.1")
    stranger = Client(HTTP_HOST="127.0.0.1")

    try:
        wx_login = assert_status(
            post_json(owner, "/api/auth/wechat-login/", {"code": f"mock:{suffix}"}),
            200,
            "wechat login",
        )
        wx_client = bearer_client(wx_login["token"])
        wx_trip = assert_status(
            post_json(wx_client, "/api/trips/", {"title": f"wechat trip {suffix}", "currency": "CNY"}),
            201,
            "create trip by bearer token",
        )["trip"]
        assert_status(wx_client.get(f"/api/trips/{wx_trip['id']}/"), 200, "bearer token can access trip")
        assert_status(wx_client.delete(f"/api/trips/{wx_trip['id']}/"), 200, "delete wx trip")

        register(owner, owner_username)
        trip = assert_status(
            post_json(
                owner,
                "/api/trips/",
                {
                    "title": "杭州三日游",
                    "location": "杭州",
                    "start_date": "2026-06-13",
                    "end_date": "2026-06-15",
                    "currency": "CNY",
                    "note": "MVP API 验证",
                },
            ),
            201,
            "create trip",
        )["trip"]

        members = assert_status(owner.get(f"/api/trips/{trip['id']}/members/"), 200, "list initial members")["members"]
        alice = members[0]
        bob = assert_status(
            post_json(owner, f"/api/trips/{trip['id']}/members/", {"display_name": "Bob"}),
            201,
            "create Bob",
        )["member"]
        carol = assert_status(
            post_json(owner, f"/api/trips/{trip['id']}/members/", {"display_name": "Carol"}),
            201,
            "create Carol",
        )["member"]
        dan = assert_status(
            post_json(owner, f"/api/trips/{trip['id']}/members/", {"display_name": "Dan"}),
            201,
            "create removable member",
        )["member"]

        bill_rows = [
            ("90.00", alice["id"], [alice["id"], bob["id"], carol["id"]], "住宿"),
            ("60.00", bob["id"], [alice["id"], bob["id"], carol["id"]], "餐饮"),
            ("30.00", carol["id"], [bob["id"], carol["id"]], "门票"),
            ("45.00", alice["id"], [alice["id"], carol["id"]], "交通"),
            ("15.00", bob["id"], [alice["id"], bob["id"]], "饮品"),
        ]

        for index, (amount, payer_id, split_ids, category) in enumerate(bill_rows, start=1):
            expense = assert_status(
                post_json(
                    owner,
                    f"/api/trips/{trip['id']}/expenses/",
                    {
                        "amount": amount,
                        "payer_id": payer_id,
                        "split_member_ids": split_ids,
                        "category": category,
                        "spent_at": f"2026-06-{12 + index:02d}",
                        "description": f"第 {index} 笔",
                    },
                ),
                201,
                f"create expense {index}",
            )["expense"]
            split_total = sum(Decimal(item["amount"]) for item in expense["splits"])
            if split_total != Decimal(amount):
                raise AssertionError(f"expense {index}: split total {split_total} != {amount}")

        summary = assert_status(owner.get(f"/api/trips/{trip['id']}/summary/"), 200, "summary")["summary"]
        if Decimal(summary["total"]) != Decimal("240.00"):
            raise AssertionError(f"summary total mismatch: {summary['total']}")
        nets = {row["display_name"]: Decimal(row["net"]) for row in summary["members"]}
        expected_nets = {
            alice["display_name"]: Decimal("55.00"),
            "Bob": Decimal("2.50"),
            "Carol": Decimal("-57.50"),
        }
        for name, expected_net in expected_nets.items():
            if nets.get(name) != expected_net:
                raise AssertionError(f"net mismatch for {name}: {nets.get(name)} != {expected_net}")

        settlements = assert_status(owner.get(f"/api/trips/{trip['id']}/settlements/"), 200, "settlements")["settlements"]
        transfer_pairs = {(item["from_member_name"], item["to_member_name"], item["amount"]) for item in settlements}
        expected_transfers = {("Carol", alice["display_name"], "55.00"), ("Carol", "Bob", "2.50")}
        if transfer_pairs != expected_transfers:
            raise AssertionError(f"settlement mismatch: {transfer_pairs}")

        paid = assert_status(
            patch_json(owner, f"/api/settlements/{settlements[0]['id']}/", {"is_paid": True}),
            200,
            "mark settlement paid",
        )["settlement"]
        if not paid["is_paid"]:
            raise AssertionError("settlement paid flag was not persisted")

        delete_blocked = assert_status(owner.delete(f"/api/members/{bob['id']}/"), 400, "delete linked member blocked")
        if "不能删除" not in delete_blocked["error"]:
            raise AssertionError(f"unexpected delete-block error: {delete_blocked}")
        assert_status(owner.delete(f"/api/members/{dan['id']}/"), 200, "delete unused member")

        register(stranger, stranger_username)
        assert_status(stranger.get(f"/api/trips/{trip['id']}/"), 404, "stranger cannot access trip")
        assert_status(stranger.get(f"/api/trips/{trip['id']}/summary/"), 404, "stranger cannot access summary")
        assert_status(owner.delete(f"/api/trips/{trip['id']}/"), 200, "delete trip with expenses")
    finally:
        Expense.objects.filter(trip__owner__username__in=[owner_username, stranger_username]).delete()
        Trip.objects.filter(owner__username__in=[owner_username, stranger_username]).delete()
        User.objects.filter(username__in=[owner_username, stranger_username]).delete()

    print("travel expense API verification passed")


if __name__ == "__main__":
    main()
