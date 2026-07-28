from django.contrib import admin

from .models import ActivityLog, GivingRecord, attendance, event, members


@admin.register(members)
class MembersAdmin(admin.ModelAdmin):
    list_display = (
        'firstname',
        'lastname',
        'role',
        'membership_status',
        'scd_group',
        'phone_number',
        'email',
    )
    search_fields = (
        'firstname',
        'lastname',
        'phone_number',
        'email',
        'role',
        'scd_group',
        'residence',
        'ministration',
    )
    list_filter = (
        'membership_status',
        'role',
        'scd_group',
        'ministration',
        'residence',
        'datejoined',
        'dateofbirth',
    )
    ordering = ('firstname', 'lastname')


@admin.register(event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'tittle',
        'date',
        'starttime',
        'endtime',
        'location',
        'category',
    )
    search_fields = (
        'tittle',
        'description',
        'location',
        'category',
    )
    list_filter = (
        'category',
        'location',
        'date',
    )
    ordering = ('-date',)


@admin.register(attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'event',
        'is_present',
        'marked_by',
        'marked_at',
    )
    search_fields = (
        'member__firstname',
        'member__lastname',
        'member__phone_number',
        'event__tittle',
        'marked_by',
    )
    list_filter = (
        'is_present',
        'event',
        'marked_at',
    )
    ordering = ('-marked_at',)
    autocomplete_fields = ('member', 'event')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'activity_type',
        'description',
        'actor',
        'icon',
        'created_at',
    )
    search_fields = (
        'activity_type',
        'description',
        'actor',
        'icon',
    )
    list_filter = (
        'activity_type',
        'actor',
        'created_at',
    )
    ordering = ('-created_at',)


@admin.register(GivingRecord)
class GivingRecordAdmin(admin.ModelAdmin):
    list_display = (
        'amount',
        'transaction_type',
        'donor_name',
        'fund',
        'payment_method',
        'gift_date',
        'tax_deductible',
        'created_at',
    )
    search_fields = (
        'donor_name',
        'fund',
        'payment_method',
        'notes',
    )
    list_filter = (
        'transaction_type',
        'fund',
        'payment_method',
        'tax_deductible',
        'gift_date',
        'created_at',
    )
    ordering = ('-created_at',)
