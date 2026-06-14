from django.conf import settings
from django.db import models


class WechatProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wechat_profile')
    openid = models.CharField(max_length=128, unique=True)
    session_key = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.openid


class ApiToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_tokens')
    key_hash = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=40, default='miniapp')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} {self.label}'


class Trip(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_trips')
    title = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=12, default='CNY')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TripMember(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    display_name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['trip', 'display_name'], name='unique_trip_member_display_name'),
            models.UniqueConstraint(
                fields=['trip', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_trip_member_user',
            ),
        ]

    def __str__(self):
        return f'{self.display_name} - {self.trip}'


class Expense(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    payer = models.ForeignKey(TripMember, on_delete=models.PROTECT, related_name='paid_expenses')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=40, default='其他')
    spent_at = models.DateField()
    description = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-spent_at', '-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='expense_amount_positive'),
        ]

    def __str__(self):
        return f'{self.trip} {self.amount}'


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='splits')
    member = models.ForeignKey(TripMember, on_delete=models.CASCADE, related_name='expense_splits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['expense', 'member'], name='unique_expense_split_member'),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='expense_split_amount_non_negative'),
        ]

    def __str__(self):
        return f'{self.member} {self.amount}'


class Settlement(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='settlements')
    from_member = models.ForeignKey(TripMember, on_delete=models.CASCADE, related_name='outgoing_settlements')
    to_member = models.ForeignKey(TripMember, on_delete=models.CASCADE, related_name='incoming_settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_paid', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['trip', 'from_member', 'to_member', 'amount'],
                name='unique_settlement_suggestion',
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='settlement_amount_positive'),
        ]

    def __str__(self):
        return f'{self.from_member} -> {self.to_member} {self.amount}'
