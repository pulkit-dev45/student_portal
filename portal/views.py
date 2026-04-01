from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
import openpyxl
from .forms import StudentDataForm
from .forms import ExcelUploadForm
from .models import studentdata, NsqfElectronics ,NsqfIT ,Dlc


# ─── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required(login_url='/login')
@ensure_csrf_cookie
def dashboard(request):
    return render(request, 'dashboard.html')


# ─── Upload ──────────────────────────────────────────────────────────────────

def parse_bool_field(value):
    """Excel cells can have True/False, 'yes'/'no', 1/0 — normalize all to bool."""
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in ['true', 'yes', '1']:
        return True
    return False


def parse_date_field(value):
    """
    Expects a string like 'JAN-2024' or 'January-2024' or 'Jan 2024'.
    Returns normalized 'JAN-2024' or empty string if nothing useful.
    """
    if not value:
        return ''
    val = str(value).strip().upper().replace(' ', '-')
    return val  # store as-is, e.g. "JAN-2024"


@login_required(login_url='/login')
def upload(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)

        if form.is_valid():
            excel_file = request.FILES['file']
            year = form.cleaned_data['year']
            session = form.cleaned_data['session']
            session_label = f"{session.upper()[:3]}-{year}"

            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active

                headers = [
                    str(cell.value).lower().strip() if cell.value else ''
                    for cell in sheet[1]
                ]

                success_count = 0
               
                duplicate_count = 0

                # 🔥 Existing roll numbers (fast lookup)
                existing_rolls = set(
                    studentdata.objects.values_list('roll_number', flat=True)
                )

                for row in sheet.iter_rows(min_row=2, values_only=True):

                    if all(cell is None for cell in row):
                        continue

                    try:
                        row_data = {
                            headers[i]: row[i]
                            for i in range(len(headers))
                            if i < len(row)
                        }

                        name = str(row_data.get('name') or '').strip()
                        roll_number = str(row_data.get('roll_number') or '').strip()
                        course_name = str(row_data.get('course_name') or '').strip()
                        scheme = str(row_data.get('scheme') or '').strip()

                        # ❌ Skip duplicate roll number
                        if roll_number and roll_number in existing_rolls:
                            duplicate_count += 1
                            continue

                        # course_hour
                        try:
                            course_hour = int(float(str(row_data.get('course_hour') or 0)))
                        except:
                            course_hour = 0

                        # fee
                        try:
                            fee = float(str(row_data.get('fee') or 0))
                        except:
                            fee = 0

                        # mode
                        mode = str(row_data.get('mode') or 'offline').lower().strip()
                        if mode not in ['offline', 'online']:
                            mode = 'offline'

                        # caste
                        caste = str(row_data.get('caste_category') or 'GENERAL').upper().strip()
                        if caste not in ['OBC', 'SC', 'ST', 'PWD', 'GENERAL']:
                            caste = 'GENERAL'

                        # center
                        center = str(row_data.get('center_name') or 'inderlok').lower().strip()
                        if center not in ['inderlok', 'janakpuri', 'karkardooma']:
                            center = 'inderlok'

                        placed = parse_bool_field(row_data.get('placed', False))
                        nsqf = str(row_data.get('nsqf') or '').strip()

                        if not name or not course_name or course_hour <= 0:
                            error_count += 1
                            continue

                        trained = parse_bool_field(row_data.get('trained', False))
                        certified = parse_bool_field(row_data.get('certified', False))

                        # auto-set dates
                        trained_date = session_label if trained else ''
                        certified_date = session_label if certified else ''

                        student = studentdata(
                            session=session_label,
                            roll_number=roll_number,
                            name=name,
                            course_name=course_name,
                            course_hour=course_hour,
                            scheme=scheme,
                            nsqf=nsqf,
                            mode=mode,
                            caste_category=caste,
                            center_name=center,
                            fee=fee,
                            trained=trained,
                            trained_date=trained_date,
                            certified=certified,
                            certified_date=certified_date,
                            placed=placed,
                        )

                        student.save()
                        success_count += 1

                        # 🔥 Add to set to prevent duplicate inside same file
                        if roll_number:
                            existing_rolls.add(roll_number)

                    except Exception as e:
                       
                        print(f"Row error: {e}")

                messages.success(
                    request,
                    f'Uploaded: {success_count} | Duplicate skipped: {duplicate_count}'
                )

            except Exception as e:
                messages.error(request, f'Error reading file: {str(e)}')

            return redirect('upload')

    else:
        form = ExcelUploadForm()

    return render(request, 'upload.html', {'form': form})


# ─── Filter (AJAX) ───────────────────────────────────────────────────────────

@login_required(login_url='/login')
def filter_students(request):
    students = studentdata.objects.all()

    center    = request.GET.get('center')
    mode      = request.GET.get('mode')
    caste     = request.GET.get('caste')
    trained   = request.GET.get('trained')    # 'true' / 'false' / ''
    certified = request.GET.get('certified')
    placed    = request.GET.get('placed')
    session   = request.GET.get('session')
    scheme = request.GET.get('scheme')
    nsqf   = request.GET.get('nsqf')   # 'yes' / 'no'

    if center:
        students = students.filter(center_name=center)
    if mode:
        students = students.filter(mode=mode)
    if caste:
        students = students.filter(caste_category=caste)
    if session:
        students = students.filter(session__icontains=session)
    if trained:
        students = students.filter(trained_date__gt='') if trained == 'true' else students.exclude(trained_date__gt='')
    if certified:
        students = students.filter(certified_date__gt='') if certified == 'true' else students.exclude(certified_date__gt='')
    if placed:
        students = students.filter(placed=(placed.lower() == 'true'))
    

    if scheme:
        students = students.filter(scheme__icontains=scheme)
    if nsqf:
        if nsqf == 'yes':
            students = students.exclude(nsqf='').exclude(nsqf__isnull=True)
        elif nsqf == 'no':
            students = students.filter(nsqf='') | students.filter(nsqf__isnull=True)

    data = [
    {
        'id':              s.id,
        'roll_number':     s.roll_number,
        'batch_code':      s.batch_code,
        'name':            s.name,
        'father_name':     s.father_name,
        'mother_name':     s.mother_name,
        'dob':             s.dob.strftime('%Y-%m-%d') if s.dob else '',
        'gender':          s.gender,
        'address':         s.address,
        'qualifications':  s.qualifications,
        'aadhaar':         s.aadhaar,
        'course_name':     s.course_name,
        'scheme':          s.scheme,
        'nsqf':            s.nsqf,
        'course_hour':     s.course_hour,
        'course_category': s.course_category,
        'center_name':     s.center_name,
        'mode':            s.mode,
        'caste_category':  s.caste_category,
        'fee':             float(s.fee),
        'claimable_amount':float(s.claimable_amount),
        'fee_date':        s.fee_date or '',
        'trained':         s.trained,
        'trained_date':    s.trained_date,
        'certified':       s.certified,
        'certified_date':  s.certified_date,
        'placed':          s.placed,
        'session':         s.session,
    }
    for s in students
]
    return JsonResponse({'results': data})


# ─── Download Report ─────────────────────────────────────────────────────────

@login_required(login_url='/login')
def download(request):
    year    = request.GET.get('year', '')
    session = request.GET.get('session', '')
    center  = request.GET.get('center', '')

    students = studentdata.objects.all()
    if year:
        students = students.filter(session__icontains=year)
    if session:
        students = students.filter(session__icontains=session)
    if center:
        students = students.filter(center_name=center)

    # Group by: category | course_name | center_name | session
    grouped = {}
    for s in students:
        key = f"{s.course_category}|{s.course_name}|{s.center_name}|{s.session}"
        if key not in grouped:
            grouped[key] = {
                'category':    s.course_category,
                'course_name': s.course_name,
                'course_hour': s.course_hour,
                'center_name': s.center_name,
                'session':     s.session,
                'scheme':      s.scheme,  
                'nsqf':        s.nsqf,  
            }
            for c in ['GENERAL', 'OBC', 'SC', 'ST', 'PWD']:
                grouped[key][c] = {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0}

        caste = s.caste_category
        grouped[key][caste]['total'] += 1
        if s.trained_date:
            grouped[key][caste]['trained'] += 1
        if s.certified_date:
            grouped[key][caste]['certified'] += 1
        if s.placed:
            grouped[key][caste]['placed'] += 1

    report_data = list(grouped.values())

    # Grand totals
    totals = {c: {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0} for c in ['GENERAL', 'OBC', 'SC', 'ST', 'PWD']}
    totals['grand_total'] = 0
    for item in report_data:
        for c in ['GENERAL', 'OBC', 'SC', 'ST', 'PWD']:
            for key in ['trained', 'certified', 'placed', 'total']:
                totals[c][key] += item[c][key]
            totals['grand_total'] += item[c]['total']
    # grand_total was being double-counted above, fix:
    totals['grand_total'] = sum(totals[c]['total'] for c in ['GENERAL', 'OBC', 'SC', 'ST', 'PWD'])

    context = {
        'data': report_data,
        'totals': totals,
        'selected_year': year,
        'selected_session': session,
        'selected_center': center,
        'years': [str(y) for y in range(2020, 2026)],
        'sessions': ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                     'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
    }
    return render(request, 'download.html', context)


# ─── API endpoint for JS-driven Excel export ─────────────────────────────────

@login_required(login_url='/login')
def api_download_data(request):
    year    = request.GET.get('year', '')
    session = request.GET.get('session', '')
    center  = request.GET.get('center', '')

    students = studentdata.objects.all()
    if year:
        students = students.filter(session__icontains=year)
    if session:
        students = students.filter(session__icontains=session)
    if center:
        students = students.filter(center_name=center)

    data = [
        {
            'course_category':  s.course_category,
            'course_name':      s.course_name,
            'course_hour':      s.course_hour,
            'center_name':      s.center_name,
            'scheme':           s.scheme ,
            'nsqf':             s.nsqf ,
            'session':          s.session,
            'caste_category':   s.caste_category,
            'trained_date':     s.trained_date,
            'certified_date':   s.certified_date,
            'placed':           s.placed,
            'fee':              float(s.fee),
            'claimable_amount': float(s.claimable_amount),
        }
        for s in students
    ]

    return JsonResponse({'results': data})


import json
@login_required(login_url='/login')
def update_student(request, student_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        student = studentdata.objects.get(id=student_id)
    except studentdata.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

    from datetime import datetime
    current_month = datetime.now().strftime('%b').upper() + '-' + datetime.now().strftime('%Y')

    try:
        body = json.loads(request.body)

        # Safe field updates with type handling
        student.name = (body.get('name') or student.name or '').strip()
        student.batch_code = (body.get('batch_code') or student.batch_code or '').strip().upper()
        student.father_name = (body.get('father_name') or student.father_name or '').strip()
        student.mother_name = (body.get('mother_name') or student.mother_name or '').strip()
        student.dob = body.get('dob') or student.dob
        student.gender = body.get('gender') or student.gender or 'Male'
        student.address = (body.get('address') or student.address or '').strip()
        student.qualifications = (body.get('qualifications') or student.qualifications or '').strip()
        student.aadhaar = (body.get('aadhaar') or student.aadhaar or '').strip()
        student.course_name = (body.get('course_name') or student.course_name or '').strip()
        student.scheme = (body.get('scheme') or student.scheme or '').strip()
        student.nsqf = (body.get('nsqf') or student.nsqf or '').strip()
        
        try:
            student.course_hour = int(body.get('course_hour') or student.course_hour or 0)
        except (ValueError, TypeError):
            student.course_hour = 0
            
        student.mode = body.get('mode') or student.mode or 'offline'
        student.caste_category = body.get('caste_category') or student.caste_category or 'GENERAL'
        student.center_name = body.get('center_name') or student.center_name or 'inderlok'
        
        try:
            student.fee = float(body.get('fee') or student.fee or 0)
        except (ValueError, TypeError):
            student.fee = 0.0
            
        student.fee_date = body.get('fee_date') or student.fee_date
        student.placed = body.get('placed', student.placed)
        student.session = (body.get('session') or student.session or '').strip()

        # trained logic
        new_trained = body.get('trained', student.trained)
        if new_trained and not student.trained:
            student.trained_date = current_month
        elif not new_trained:
            student.trained_date = ''
        student.trained = new_trained

        # certified logic
        new_certified = body.get('certified', student.certified)
        if new_certified and not student.certified:
            student.certified_date = current_month
        elif not new_certified:
            student.certified_date = ''
        student.certified = new_certified

        student.save()

        return JsonResponse({
            'success': True,
            'course_category': student.course_category,
            'claimable_amount': float(student.claimable_amount),
            'trained_date': student.trained_date,
            'certified_date': student.certified_date,
        })

    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Invalid JSON: {str(e)}'}, status=400)
    except Exception as e:
        import traceback
        error_msg = str(e)
        tb = traceback.format_exc()
        print(f"Update student error: {error_msg}\n{tb}")
        return JsonResponse({'success': False, 'error': error_msg}, status=400)

    # trained logic
    new_trained = body.get('trained', student.trained)
    if new_trained and not student.trained:
        # just switched ON — auto-set date
        student.trained_date = current_month
    elif not new_trained:
        # switched OFF — clear date
        student.trained_date = ''
    student.trained = new_trained

    # certified logic
    new_certified = body.get('certified', student.certified)
    if new_certified and not student.certified:
        student.certified_date = current_month
    elif not new_certified:
        student.certified_date = ''
    student.certified = new_certified

    student.save()

    return JsonResponse({
        'success':          True,
        'course_category':  student.course_category,
        'claimable_amount': float(student.claimable_amount),
        'trained_date':     student.trained_date,
        'certified_date':   student.certified_date,
    })

def inputView(request):
    if request.method=='POST':
        form=StudentDataForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    
    else:
        form=StudentDataForm()
    
    context = {
        'form': form,
        'months': ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
        'years': list(range(2020, 2031)),
    }
    return render(request,"input.html",context)

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


def get_summary_for_queryset(queryset):
    summary = {
        'Total': queryset.count(),
        'SC': 0,
        'ST': 0,
        'OBC': 0,
        'PWD': 0,
        'GENERAL': 0,
        'B': 0,
        'C': 0,
        'D': 0,
        'E': 0,
    }
    for s in queryset:
        caste = s.caste_category
        if caste in summary:
            summary[caste] += 1

        course_cat = (s.course_category or '').strip().upper()
        if course_cat.startswith('B'):
            summary['B'] += 1
        elif course_cat.startswith('C'):
            summary['C'] += 1
        elif course_cat.startswith('D'):
            summary['D'] += 1
        elif course_cat.startswith('E'):
            summary['E'] += 1

    return summary


@login_required(login_url='/login')
def overview(request):
    selected_session = request.GET.get('session', '')

    students = studentdata.objects.all()
    if selected_session:
        students = students.filter(session=selected_session)

    centers = [
        ('Inderlok', get_summary_for_queryset(students.filter(center_name='inderlok'))),
        ('Janakpuri', get_summary_for_queryset(students.filter(center_name='janakpuri'))),
        ('Karkardooma', get_summary_for_queryset(students.filter(center_name='karkardooma'))),
    ]

    sessions = list(
        studentdata.objects
            .values_list('session', flat=True)
            .distinct()
            .order_by('-session')
    )

    context = {
        'all_record': students.count(),
        'centers': centers,
        'sessions': sessions,
        'selected_session': selected_session,
    }

    return render(request, 'overview.html', context)





# old summary code removed; overview is now implemented above with dynamic sessions and optional filters


@login_required(login_url='/login')
def overview_data(request):
    selected_session = request.GET.get('session', '')

    students = studentdata.objects.all()
    if selected_session:
        students = students.filter(session=selected_session)

    centers = [
        {
            'name': 'Inderlok',
            'stats': get_summary_for_queryset(students.filter(center_name='inderlok'))
        },
        {
            'name': 'Janakpuri',
            'stats': get_summary_for_queryset(students.filter(center_name='janakpuri'))
        },
        {
            'name': 'Karkardooma',
            'stats': get_summary_for_queryset(students.filter(center_name='karkardooma'))
        },
    ]

    sessions = list(
        studentdata.objects
            .values_list('session', flat=True)
            .distinct()
            .order_by('-session')
    )

    return JsonResponse({
        'all_record': students.count(),
        'centers': centers,
        'sessions': sessions,
        'selected_session': selected_session,
    })

def courses(request):
    It=NsqfIT.objects.all()
    elctro=NsqfElectronics.objects.all()
    dlc=Dlc.objects.all()
    return render(request,"view_courses.html",locals())