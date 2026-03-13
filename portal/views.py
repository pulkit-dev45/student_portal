from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import StudentDataForm, ExcelUploadForm
from .models import studentdata
from django.contrib import messages
from django.contrib.auth import authenticate , login , logout
from django.contrib.auth.decorators import login_required
import openpyxl

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')  # or any page you want
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='/login')
def dashboard(request):
    return render(request, "dashboard.html")


@login_required(login_url='/login')
def upload(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            year = form.cleaned_data['year']
            session = form.cleaned_data['session']
            
            try:
                # Load the workbook
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                
                # Get headers from first row
                headers = []
                for cell in sheet[1]:
                    headers.append(str(cell.value).lower().strip() if cell.value else '')
                
                print("Headers found:", headers)
                
                success_count = 0
                error_count = 0
                
                # Loop through data rows (starting from row 2)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Stop if row is completely empty
                    if all(cell is None for cell in row):
                        continue
                        
                    try:
                        # Create a dictionary of row data
                        row_data = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                row_data[header] = row[i]
                        
                        print("Processing row:", row_data)
                        
                        # Extract values
                        name = str(row_data.get('name', '')).strip() if row_data.get('name') else ''
                        course_name = str(row_data.get('course_name', '')).strip() if row_data.get('course_name') else ''
                        
                        # Handle course hour
                        course_hour = row_data.get('course_hour', 0)
                        try:
                            course_hour = int(float(str(course_hour))) if course_hour else 0
                        except:
                            course_hour = 0
                        
                        # Handle mode
                        mode = str(row_data.get('mode', 'offline')).lower().strip()
                        if mode not in ['offline', 'online']:
                            mode = 'offline'
                        
                        # Handle caste
                        caste = str(row_data.get('caste_category', 'GENERAL')).upper().strip()
                        valid_castes = ['OBC', 'SC', 'ST', 'PWD', 'GENERAL']
                        if caste not in valid_castes:
                            caste = 'GENERAL'
                        
                        # Handle center
                        center = str(row_data.get('center_name', 'inderlok')).lower().strip()
                        valid_centers = ['inderlok', 'janakpuri', 'karkardooma']
                        if center not in valid_centers:
                            center = 'inderlok'
                        
                        # Handle scheme
                        scheme = str(row_data.get('scheme', '')).strip() if row_data.get('scheme') else ''
                        
                        # Handle boolean fields
                        trained = row_data.get('trained', False)
                        if trained in [True, 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes', '1', 1]:
                            trained = True
                        else:
                            trained = False
                        
                        certified = row_data.get('certified', False)
                        if certified in [True, 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes', '1', 1]:
                            certified = True
                        else:
                            certified = False
                        
                        placed = row_data.get('placed', False)
                        if placed in [True, 'TRUE', 'True', 'true', 'YES', 'Yes', 'yes', '1', 1]:
                            placed = True
                        else:
                            placed = False
                        
                        # Validate required fields
                        if name and course_name and course_hour > 0:
                            # Create student data object
                            student = studentdata(
                                session=f"{session} {year}",  # Now this will work with CharField
                                name=name,
                                course_name=course_name,
                                course_hour=course_hour,
                                scheme=scheme,
                                mode=mode,
                                caste_category=caste,
                                center_name=center,
                                trained=trained,
                                certified=certified,
                                placed=placed
                            )
                            student.save()
                            success_count += 1
                            print(f"Saved: {name} - {course_name}")
                        else:
                            error_count += 1
                            print(f"Skipped row - missing required fields: name={name}, course={course_name}, hours={course_hour}")
                            
                    except Exception as e:
                        error_count += 1
                        print(f"Error saving row: {str(e)}")
                
                messages.success(request, f'Successfully uploaded {success_count} records. Skipped: {error_count}')
                
            except Exception as e:
                messages.error(request, f'Error reading Excel file: {str(e)}')
                print(f"File error: {str(e)}")
            
            return redirect('upload')
    else:
        form = ExcelUploadForm()

    return render(request, 'upload.html', {'form': form})
@login_required(login_url='/login')
def filter_students(request):
    center = request.GET.get("center")
    mode = request.GET.get("mode")
    caste = request.GET.get("caste")
    trained = request.GET.get("trained")
    certified = request.GET.get("certified")
    placed = request.GET.get("placed")

    students = studentdata.objects.all()

    if center:
        students = students.filter(center_name=center)
    if mode:
        students = students.filter(mode=mode)
    if caste:
        students = students.filter(caste_category=caste)
    if trained:
        if trained.lower() == 'true':
            students = students.filter(trained=True)
        elif trained.lower() == 'false':
            students = students.filter(trained=False)
    if certified:
        if certified.lower() == 'true':
            students = students.filter(certified=True)
        elif certified.lower() == 'false':
            students = students.filter(certified=False)
    if placed:
        if placed.lower() == 'true':
            students = students.filter(placed=True)
        elif placed.lower() == 'false':
            students = students.filter(placed=False)

    data = []
    for student in students:
        hours = student.course_hour

        # Course category logic
        if hours > 500:
            category = "B - Long Term Course"
        elif 90 <= hours <= 500:
            category = "C - Short Term Course"
        elif hours < 90:
            category = "D - Short Term Course"
        else:
            category = "E - DLC (CCC/CCC+/BCC)"

        data.append({
            "name": student.name,
            "course_name": student.course_name,
            "course_hour": student.course_hour,
            "course_category": category,
            "center_name": student.center_name,
            "mode": student.mode,
            "caste_category": student.caste_category,
            "trained": student.trained,
            "certified": student.certified,
            "placed": student.placed,
            "session": student.session,
        })
    
    return JsonResponse({"results": data})

@login_required(login_url='/login')
def download(request):
    # Get filter parameters
    year = request.GET.get("year", "")
    session = request.GET.get("session", "")
    center = request.GET.get("center", "")

    # Get all students
    students = studentdata.objects.all()

    # Apply filters
    if year:
        students = students.filter(session__icontains=year)
    if session:
        students = students.filter(session__icontains=session)
    if center:
        students = students.filter(center_name=center)

    # Process data and group it in Python instead of template
    grouped_data = {}
    
    for s in students:
        hours = s.course_hour
        if hours > 500:
            category = "B - Long Term"
        elif hours >= 90:
            category = "C - Short Term"
        elif hours < 90:
            category = "D - Short Term"
        else:
            category = "E - DLC"

        # Create a unique key for grouping
        key = f"{category}|{s.course_name}|{s.center_name}|{s.session}"
        
        if key not in grouped_data:
            grouped_data[key] = {
                'category': category,
                'course_name': s.course_name,
                'center_name': s.center_name,
                'session': s.session,
                'GENERAL': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
                'OBC': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
                'SC': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
                'ST': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
                'PWD': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
            }
        
        # Update counts
        caste = s.caste_category
        grouped_data[key][caste]['total'] += 1
        if s.trained:
            grouped_data[key][caste]['trained'] += 1
        if s.certified:
            grouped_data[key][caste]['certified'] += 1
        if s.placed:
            grouped_data[key][caste]['placed'] += 1

    # Convert to list for template
    report_data = list(grouped_data.values())

    # Calculate totals
    totals = {
        'GENERAL': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
        'OBC': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
        'SC': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
        'ST': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
        'PWD': {'trained': 0, 'certified': 0, 'placed': 0, 'total': 0},
        'grand_total': 0
    }
    
    for item in report_data:
        for caste in ['GENERAL', 'OBC', 'SC', 'ST', 'PWD']:
            totals[caste]['trained'] += item[caste]['trained']
            totals[caste]['certified'] += item[caste]['certified']
            totals[caste]['placed'] += item[caste]['placed']
            totals[caste]['total'] += item[caste]['total']
            totals['grand_total'] += item[caste]['total']

    context = {
        'data': report_data,
        'totals': totals,
        'selected_year': year,
        'selected_session': session,
        'selected_center': center,
        'years': ['2020', '2021', '2022', '2023', '2024', '2025'],
        'sessions': ['January', 'February', 'March', 'April', 'May', 'June', 
                    'July', 'August', 'September', 'October', 'November', 'December'],
    }
    return render(request, 'download.html', context)

from django.http import JsonResponse
@login_required(login_url='/login')
def api_download_data(request):
    year = request.GET.get("year", "")
    session = request.GET.get("session", "")
    center = request.GET.get("center", "")

    students = studentdata.objects.all()
    
    if year:
        students = students.filter(session__icontains=year)
    if session:
        students = students.filter(session__icontains=session)
    if center:
        students = students.filter(center_name=center)

    data = []
    for s in students:
        hours = s.course_hour
        if hours > 500:
            cat = "B - Long Term"
        elif hours >= 90:
            cat = "C - Short Term"
        elif hours < 90:
            cat = "D - Short Term"
        else:
            cat = "E - DLC"

        data.append({
            "course_category": cat,
            "course_name": s.course_name,
            "center_name": s.center_name,
            "session": s.session,
            "caste_category": s.caste_category,
            "trained": s.trained,
            "certified": s.certified,
            "placed": s.placed,
        })
    
    return JsonResponse({"results": data})