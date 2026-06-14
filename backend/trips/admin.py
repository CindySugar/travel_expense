from django.contrib import admin

from .models import ApiToken, Expense, ExpenseSplit, Settlement, Trip, TripMember, WechatProfile


class TripMemberInline(admin.TabularInline):
    model = TripMember
    extra = 0


class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'location', 'start_date', 'end_date', 'currency', 'created_at')
    search_fields = ('title', 'location', 'owner__username')
    inlines = [TripMemberInline]


@admin.register(TripMember)
class TripMemberAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'trip', 'user', 'created_at')
    search_fields = ('display_name', 'trip__title', 'user__username')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('trip', 'payer', 'amount', 'category', 'spent_at', 'created_by')
    list_filter = ('category', 'spent_at')
    search_fields = ('trip__title', 'payer__display_name', 'description')
    inlines = [ExpenseSplitInline]


@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    list_display = ('expense', 'member', 'amount')


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('trip', 'from_member', 'to_member', 'amount', 'is_paid', 'paid_at')
    list_filter = ('is_paid',)


@admin.register(WechatProfile)
class WechatProfileAdmin(admin.ModelAdmin):
    list_display = ('openid', 'user', 'created_at', 'updated_at')
    search_fields = ('openid', 'user__username')


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'label', 'created_at', 'last_used_at')
    search_fields = ('user__username', 'label')
