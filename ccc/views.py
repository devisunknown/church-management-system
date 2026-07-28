from datetime import datetime
from itertools import groupby
from operator import attrgetter

from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from ratelimit import RateLimitDecorator

login_rate_limit = RateLimitDecorator(calls=5, period=60)
signup_rate_limit = RateLimitDecorator(calls=3, period=60)

from .models import ActivityLog, GivingRecord, attendance, event, members as Member



def _log_activity(activity_type, description, icon='info', actor=''):

    ActivityLog.objects.create(
        activity_type=activity_type,
        description=description,
        icon=icon,
        actor=actor,
    )



@login_required
def dashboard(request):
    latest_attendance_event = attendance.objects.order_by('-marked_at').values_list('event_id', flat=True).first()
    weekly_attendance = 0
    if latest_attendance_event:
        weekly_attendance = attendance.objects.filter(event_id=latest_attendance_event, is_present=True).count()

    latest_giving = GivingRecord.objects.filter(transaction_type='income').order_by('-created_at').first()
    recent_giving = latest_giving.amount if latest_giving else None

    context = {
        'total_members': Member.objects.count(),
        'total_events': event.objects.count(),
        'activeevents': event.objects.all()[:5],
        'recent_activity': ActivityLog.objects.all()[:6],
        'weekly_attendance': weekly_attendance,
        'recent_giving': recent_giving,
    }
    return render(request, 'dashboard.html', context)


@login_rate_limit
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or 'dashboard')

        return render(request, 'login.html', {'error': 'Invalid username or password.'})

    return render(request, 'login.html')


@signup_rate_limit
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')

        User.objects.create_user(username=username, email=email, password=password)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')

    return render(request, 'signup.html')



@login_required
def members_view(request):
    all_members = Member.objects.all()[:6]
    return render(request, 'members.html', {'members': all_members})


@login_required
def member_search(request):
    """AJAX endpoint used by the donor search field on addmoney.html."""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    members = Member.objects.filter(
        Q(firstname__icontains=query) |
        Q(lastname__icontains=query) |
        Q(phone_number__icontains=query) |
        Q(email__icontains=query)
    )[:8]

    results = [
        {
            'id': m.id,
            'name': m.full_name,
            'phone': m.phone_number or '',
            'initials': m.initials,
        }
        for m in members
    ]
    return JsonResponse({'results': results})


@login_required
def addmember(request):
    if request.method == 'POST':
        firstname = request.POST.get('firstname', '')
        lastname = request.POST.get('lastname', '')
        email = request.POST.get('email', '')
        phonenumber = request.POST.get('phonenumber', '')
        preferedcontact = request.POST.get('preferedcontact', 'Email')
        membership_status = request.POST.get('status', 'active')
        datejoined = request.POST.get('datejoined')
        residence = request.POST.get('residence', '')
        address = request.POST.get('address', '')
        scdgroup = request.POST.get('group', '')
        uploaded_image = request.FILES.get('image')
        roles = request.POST.get('Roles')

        parsed_datejoined = None
        if datejoined:
            try:
                parsed_datejoined = datetime.strptime(datejoined, '%Y-%m-%d')
            except ValueError:
                parsed_datejoined = None

        try:
            new_member = Member.objects.create(
                firstname=firstname,
                lastname=lastname,
                email=email,
                phone_number=phonenumber,
                residence=residence or address or '',
                ministration=preferedcontact,
                address=address or '',
                datejoined=parsed_datejoined,
                scd_group=scdgroup,
                image=uploaded_image,
                role=roles,
                membership_status=membership_status,
            )
        except IntegrityError:
            return render(request, 'addmember.html', {
                'error': 'A member with this phone number already exists.',
                'email': email,
                'phonenumber': phonenumber,
            })

        _log_activity(
            activity_type='member_added',
            description=f"New Member: {new_member.full_name}",
            icon='person_add',
            actor=request.user.username if request.user.is_authenticated else '',
        )
        return redirect('members')

    return render(request, 'addmember.html')


@login_required
def editmember(request, member_id):
    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return redirect('members')

    if request.method == 'POST':
        firstname = request.POST.get('firstname', '')
        lastname = request.POST.get('lastname', '')
        email = request.POST.get('email', '')
        phonenumber = request.POST.get('phonenumber', '')
        preferedcontact = request.POST.get('preferedcontact', 'Email')
        membership_status = request.POST.get('status', 'active')
        datejoined = request.POST.get('datejoined')
        residence = request.POST.get('residence', '')
        address = request.POST.get('address', '')
        scdgroup = request.POST.get('group', '')
        roles = request.POST.get('Roles')
        uploaded_image = request.FILES.get('image')

        parsed_datejoined = None
        if datejoined:
            try:
                parsed_datejoined = datetime.strptime(datejoined, '%Y-%m-%d')
            except ValueError:
                parsed_datejoined = None

        member.firstname = firstname
        member.lastname = lastname
        member.email = email
        member.phone_number = phonenumber
        member.ministration = preferedcontact
        member.membership_status = membership_status
        member.residence = residence or address or ''
        member.address = address or ''
        if parsed_datejoined:
            member.datejoined = parsed_datejoined
        member.scd_group = scdgroup
        if uploaded_image:
            member.image = uploaded_image
        member.role = roles

        try:
            member.save()
            _log_activity(
                activity_type='member_added',
                description=f"Member Updated: {member.full_name}",
                icon='person',
                actor=request.user.username if request.user.is_authenticated else '',
            )
            return redirect('members')
        except IntegrityError:
            return render(request, 'editmember.html', {
                'error': 'A member with this phone number already exists.',
                'member': member,
            })

    return render(request, 'editmember.html', {'member': member})


def _volunteer_status_for_event(ev):
    if not ev:
        return []

    all_members = list(Member.objects.exclude(role='').exclude(role__isnull=True))
    roles = sorted({(m.role or '').strip() for m in all_members if (m.role or '').strip()})

    marked_present_ids = set(
        attendance.objects.filter(event=ev, is_present=True).values_list('member_id', flat=True)
    )

    statuses = []
    for role_name in roles:
        role_members = [m for m in all_members if (m.role or '').strip() == role_name]
        total = len(role_members)
        if total == 0:
            continue
        filled = sum(1 for m in role_members if m.id in marked_present_ids)
        ratio = filled / total

        if ratio >= 1:
            level = 'full'
        elif ratio <= 0.3:
            level = 'critical'
        else:
            level = 'partial'

        statuses.append({
            'role': role_name,
            'filled': filled,
            'total': total,
            'percent': min(round(ratio * 100), 100),
            'level': level,
        })

    return statuses


@login_required
def calandar(request):
    selected_date_str = request.GET.get('date') or request.GET.get('selected_date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    view_mode = request.GET.get('view', 'weekly')

    if view_mode == 'monthly':
        first_day_of_month = selected_date.replace(day=1)
        if selected_date.month == 12:
            first_day_next_month = first_day_of_month.replace(year=selected_date.year + 1, month=1)
        else:
            first_day_next_month = first_day_of_month.replace(month=selected_date.month + 1)
        last_day_of_month = first_day_next_month - timezone.timedelta(days=1)
        dates_list = [first_day_of_month + timezone.timedelta(days=i) for i in range((last_day_of_month - first_day_of_month).days + 1)]
    else:
        days_since_monday = selected_date.weekday()
        week_start = selected_date - timezone.timedelta(days=days_since_monday)
        dates_list = [week_start + timezone.timedelta(days=i) for i in range(7)]

    events = event.objects.filter(date__date=selected_date).order_by('starttime')

    next_service = (
        event.objects.filter(date__gte=timezone.now())
        .order_by('date', 'starttime')
        .first()
    )
    volunteer_status = _volunteer_status_for_event(next_service)

    return render(request, 'calandar.html', {
        'events': events,
        'selected_date': selected_date,
        'dates_list': dates_list,
        'view_mode': view_mode,
        'next_service': next_service,
        'volunteer_status': volunteer_status,
    })

@login_required
def events_view(request):
    all_events = event.objects.all()
    return render(request, 'events.html', {'events': all_events})


@login_required
def addevent(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        if not title or not description:
            return render(request, 'add event.html', {
                'error': 'Title and description are required.',
            })

        new_event = event.objects.create(
            tittle=title,
            description=description,
            date=request.POST.get('event_date'),
            starttime=request.POST.get('start_time'),
            endtime=request.POST.get('end_time'),
            location=request.POST.get('venue') or request.POST.get('street_address', ''),
            category=request.POST.get('category'),
        )

        _log_activity(
            activity_type='event_created',
            description=f"Event Created: {new_event.tittle}",
            icon='calendar_month',
            actor=request.user.username if request.user.is_authenticated else '',
        )
        return redirect('events')

    return render(request, 'add event.html')


@login_required
def attendance_landing(request):

    ev = event.objects.order_by('-date', '-id').first()
    if ev:
        return redirect('take_attendance', event_id=ev.id)
    return redirect('events')


@login_required
def history_view(request):
    activity_logs = ActivityLog.objects.all()[:50]
    categories = sorted({log.get_activity_type_display() for log in activity_logs if log.get_activity_type_display()})
    users = sorted({log.actor for log in activity_logs if log.actor})
    return render(request, 'history.html', {
        'activity_logs': activity_logs,
        'activity_categories': categories,
        'activity_users': users,
    })


@login_required
def take_attendance(request, event_id):
    ev = get_object_or_404(event, id=event_id)

    if request.method == 'POST':
        present_ids = set(request.POST.getlist('present_members'))
        all_members = Member.objects.all()

        for m in all_members:
            attendance.objects.update_or_create(
                member=m,
                event=ev,
                defaults={
                    'is_present': str(m.id) in present_ids,
                    'marked_by': request.user.username if request.user.is_authenticated else None,
                },
            )

        _log_activity(
            activity_type='attendance_taken',
            description=f"Attendance taken for {ev.tittle} ({len(present_ids)} present)",
            icon='event_available',
            actor=request.user.username if request.user.is_authenticated else '',
        )
        return redirect('attendance_summary', event_id=ev.id)

    all_members = Member.objects.all().order_by('scd_group', 'firstname')
    role_filters = sorted(
        {
            (member.role or '').strip()
            for member in all_members
            if (member.role or '').strip()
        }
    )
    scd_group_filters = sorted(
        {
            (member.scd_group or '').strip()
            for member in all_members
            if (member.scd_group or '').strip()
        }
    )
    existing = {
        rec.member_id: rec.is_present
        for rec in attendance.objects.filter(event=ev)
    }

    grouped = []
    for group_name, members_iter in groupby(all_members, key=attrgetter('scd_group')):
        member_list = list(members_iter)
        for m in member_list:
            m.is_marked_present = existing.get(m.id, False)
        grouped.append({
            'group_name': group_name or 'Unassigned',
            'members': member_list,
        })

    return render(request, 'attendance.html', {
        'event': ev,
        'grouped_members': grouped,
        'role_filters': role_filters,
        'scd_group_filters': scd_group_filters,
    })


@login_required
def attendance_summary(request, event_id):
    ev = get_object_or_404(event, id=event_id)
    records = attendance.objects.filter(event=ev).select_related('member')

    present = [r for r in records if r.is_present]
    absent = [r for r in records if not r.is_present]
    attendees = [
        {
            'id': rec.member.id,
            'full_name': rec.member.full_name,
            'role': rec.member.role or 'unassigned',
            'scd_group': rec.member.scd_group or 'Unassigned',
            'status': 'present' if rec.is_present else 'absent',
            'initials': rec.member.initials,
            'photo': rec.member.photo.url if rec.member.photo else '',
        }
        for rec in records
    ]
    present_attendees = [attendee for attendee in attendees if attendee['status'] == 'present']
    absent_attendees = [attendee for attendee in attendees if attendee['status'] == 'absent']
    role_filters = sorted({
        (rec.member.role or '').strip()
        for rec in records
        if (rec.member.role or '').strip()
    })
    scd_group_filters = sorted({
        (rec.member.scd_group or '').strip()
        for rec in records
        if (rec.member.scd_group or '').strip()
    })

    return render(request, 'attendance summary.html', {
        'event': ev,
        'present': present,
        'absent': absent,
        'present_count': len(present),
        'absent_count': len(absent),
        'total_count': len(present) + len(absent),
        'attendees': attendees,
        'present_attendees': present_attendees,
        'absent_attendees': absent_attendees,
        'role_filters': role_filters,
        'scd_group_filters': scd_group_filters,
    })



@login_required
def money(request):
    records = GivingRecord.objects.all()[:10]
    total_income = GivingRecord.objects.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_deductions = GivingRecord.objects.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_giving = total_income - total_deductions

    month_labels = []
    monthly_totals = []
    today = timezone.localdate()
    start_year = today.year
    start_month_num = today.month - 5
    while start_month_num <= 0:
        start_month_num += 12
        start_year -= 1

    ordered_months = []
    for i in range(6):
        year = start_year + ((start_month_num - 1 + i) // 12)
        month_num = ((start_month_num - 1 + i) % 12) + 1
        ordered_months.append((year, month_num))

    for year, month in ordered_months:
        month_labels.append(datetime(year, month, 1).strftime('%b'))
        month_income = GivingRecord.objects.filter(
            transaction_type='income',
            gift_date__year=year,
            gift_date__month=month,
        ).aggregate(total=Sum('amount'))['total'] or 0
        month_expense = GivingRecord.objects.filter(
            transaction_type='expense',
            gift_date__year=year,
            gift_date__month=month,
        ).aggregate(total=Sum('amount'))['total'] or 0
        monthly_totals.append(float(month_income - month_expense))

    fund_totals_raw = (
        GivingRecord.objects.filter(transaction_type='income')
        .values('fund')
        .annotate(total=Sum('amount'))
        .order_by('fund')
    )
    fund_totals = {row['fund']: float(row['total'] or 0) for row in fund_totals_raw}
    fund_labels = [label for value, label in GivingRecord.FUND_CHOICES]
    fund_values = [fund_totals.get(value, 0) for value, _ in GivingRecord.FUND_CHOICES]

    
    recent_donors = []
    seen_names = set()
    member_lookup = {
        m.full_name.strip().lower(): m
        for m in Member.objects.all()
    }

    for rec in GivingRecord.objects.filter(transaction_type='income').exclude(donor_name='').order_by('-gift_date', '-created_at'):
        name = rec.donor_name.strip()
        key = name.lower()
        if not name or key in seen_names:
            continue
        seen_names.add(key)

        matched_member = member_lookup.get(key)
        donor_total = GivingRecord.objects.filter(transaction_type='income', donor_name__iexact=name).aggregate(
            total=Sum('amount')
        )['total'] or 0

        recent_donors.append({
            'name': name,
            'initials': matched_member.initials if matched_member else (name[:2].upper() if name else '??'),
            'photo': matched_member.photo.url if matched_member and matched_member.photo else '',
            'is_member': matched_member is not None,
            'last_gift_date': rec.gift_date,
            'last_amount': rec.amount,
            'total_given': donor_total,
        })

        if len(recent_donors) >= 6:
            break

    return render(request, 'money.html', {
        'records': records,
        'total_giving': total_giving,
        'total_income': total_income,
        'total_deductions': total_deductions,
        'month_labels': month_labels,
        'monthly_totals': monthly_totals,
        'fund_labels': fund_labels,
        'fund_values': fund_values,
        'recent_donors': recent_donors,
    })


@login_required
def addmoney(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type', 'income')
        if transaction_type not in dict(GivingRecord.TRANSACTION_TYPE_CHOICES):
            transaction_type = 'income'
        donor_name = request.POST.get('donor_name', '').strip()
        fund = request.POST.get('fund', 'general')
        payment_method = request.POST.get('payment_method', 'cash')
        gift_date = request.POST.get('gift_date') or timezone.localdate()
        tax_deductible = request.POST.get('tax_deductible') == 'on'
        notes = request.POST.get('notes', '').strip()

        GivingRecord.objects.create(
            amount=amount,
            transaction_type=transaction_type,
            donor_name=donor_name,
            fund=fund,
            payment_method=payment_method,
            gift_date=gift_date,
            tax_deductible=tax_deductible,
            notes=notes,
        )

        if transaction_type == 'expense':
            _log_activity(
                activity_type='giving_recorded',
                description=f"Deduction recorded: {donor_name or notes or 'Expense'} — {amount}",
                icon='remove_circle',
                actor=request.user.username if request.user.is_authenticated else '',
            )
        else:
            _log_activity(
                activity_type='giving_recorded',
                description=f"Gift recorded: {donor_name or 'Anonymous'} — {amount}",
                icon='payments',
                actor=request.user.username if request.user.is_authenticated else '',
            )
        return redirect('money')

    return render(request, 'addmoney.html', {
        'today': timezone.localdate(),
    })