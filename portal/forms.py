from django import forms
from .models import studentdata
from datetime import datetime

# ModelForm for studentdata
class StudentDataForm(forms.ModelForm):
    class Meta:
        model = studentdata
        fields = '__all__'

# Simple form to upload Excel
class ExcelUploadForm(forms.Form):
    # Generate years from 2020 to current year + 1
    current_year = datetime.now().year
    YEAR_CHOICES = [(str(year), str(year)) for year in range(2020, current_year + 2)]
    
    SESSION_CHOICES = [
        ('January', 'January'),
        ('February', 'February'),
        ('March', 'March'),
        ('April', 'April'),
        ('May', 'May'),
        ('June', 'June'),
        ('July', 'July'),
        ('August', 'August'),
        ('September', 'September'),
        ('October', 'October'),
        ('November', 'November'),
        ('December', 'December'),
    ]
    
    year = forms.ChoiceField(choices=YEAR_CHOICES, required=True, widget=forms.Select(attrs={'class': 'filter-select'}))
    session = forms.ChoiceField(choices=SESSION_CHOICES, required=True, widget=forms.Select(attrs={'class': 'filter-select'}))
    file = forms.FileField(widget=forms.FileInput(attrs={'class': 'file-input'}))