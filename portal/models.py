from django.db import models

DLC_KEYWORDS = ['ccc', 'bcc', 'ccc+']

def get_course_category(course_name, course_hour):
    if not course_name or not course_hour:
        return 'D - Short Term Course'
    name_lower = course_name.lower()
    if any(kw in name_lower for kw in DLC_KEYWORDS):
        return 'E - DLC'
    if course_hour > 500:
        return 'B - Long Term Course'
    if 90 <= course_hour <= 500:
        return 'C - Short Term Course'
    return 'D - Short Term Course'


class studentdata(models.Model):
    MODE_CHOICES = [
        ('offline', 'Off Campus'),
        ('online', 'On Campus'),
    ]
    NSQF_LEVEL=[
        ("Level 1","Level 1"),
        ("Level 2","Level 2"),
        ("Level 3","Level 3"),
        ("Level 4","Level 4"),
        ("Level 5","Level 5"),
        ("Level 6","Level 6"),
    ]
    HIGHEST_QUALIFICATION = [
        ("10+2 / ITI / Pursuing Graduation", "10+2 / ITI / Pursuing Graduation"),
        ("Graduation (B.Sc / B.Com / BA / BBA)", "Graduation (B.Sc / B.Com / BA / BBA)"),
        ("Technical (CS / IT / BCA / B.Tech)", "Technical (CS / IT / BCA / B.Tech)"),
        ("Post Graduate", "Post Graduate"),
        ("MCA / M.Tech", "MCA / M.Tech"),
        ("Other", "Other"),
    ]
    GENDER = [
        ("Male","Male"),
        ("Female","Female"),
    ]
    CASTE_CHOICES = [
        ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST'),
        ('PWD', 'PWD'), ('GENERAL', 'GENERAL'),
    ]
    CENTER_CHOICES = [
        ('inderlok', 'Inderlok'),
        ('janakpuri', 'Janakpuri'),
        ('karkardooma', 'Karkardooma'),
    ]

    session          = models.CharField(max_length=20, null=True, blank=True)
    batch_code       = models.CharField(max_length=20,null=True,blank=True)
    roll_number      = models.CharField(max_length=20, blank=True, null=True)
    name             = models.CharField(max_length=100 , null=True,blank=True)
    father_name      = models.CharField(max_length=50 ,null=True,blank=True)
    mother_name      = models.CharField(max_length=50,null=True,blank=True)
    dob              = models.DateField(null=True, blank=True)
    gender           = models.CharField(max_length=10, choices=GENDER, null=True, blank=True)
    qualifications   = models.CharField(max_length=50, null=True, blank=True ,choices=HIGHEST_QUALIFICATION)
    address          = models.CharField(max_length=100, null=True, blank=True)
    aadhaar          = models.CharField(max_length=12, null=True, blank=True)
    course_name      = models.CharField(max_length=100, null=True, blank=True)
    course_hour      = models.PositiveIntegerField(null=True, blank=True)
    course_category  = models.CharField(max_length=30, blank=True, null=True)
    scheme           = models.CharField(max_length=50, blank=True, null=True)
    nsqf             = models.CharField(max_length=20, blank=True, null=True ,choices=NSQF_LEVEL)
    mode             = models.CharField(max_length=10, choices=MODE_CHOICES, default='offline')
    caste_category   = models.CharField(max_length=10, choices=CASTE_CHOICES, default='GENERAL')
    center_name      = models.CharField(max_length=30, choices=CENTER_CHOICES, default='inderlok')
    fee              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    claimable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fee_date         = models.DateField(null=True, blank=True)
    trained          = models.BooleanField(default=False ,)
    trained_date     = models.CharField(max_length=20, blank=True, null=True)
    certified        = models.BooleanField(default=False)
    certified_date   = models.CharField(max_length=20, blank=True, null=True)
    placed           = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.course_category = get_course_category(self.course_name, self.course_hour)
        if self.certified:
            self.claimable_amount = self.fee
        elif self.trained:
            self.claimable_amount = self.fee * 70 / 100
        else:
            self.claimable_amount = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.course_name} ({self.caste_category})"
    


class NsqfElectronics(models.Model):
    course_name=models.CharField(max_length=40)
    nsqf_level=models.PositiveIntegerField(max_length=2)
    hours=models.PositiveIntegerField(max_length=5)

    def __str__(self):
        return f"{self.course_name}--{self.nsqf_level}--{self.hours}"


class NsqfIT(models.Model):
    course_name=models.CharField(max_length=40)
    nsqf_level=models.PositiveIntegerField(max_length=2)
    hours=models.PositiveIntegerField(max_length=5)

    def __str__(self):
        return f"{self.course_name}--{self.nsqf_level}--{self.hours}"
class Dlc(models.Model):
    course_name=models.CharField(max_length=40)

    def __str__(self):
        return f"{self.course_name}"

