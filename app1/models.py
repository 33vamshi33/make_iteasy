from django.db import models
from django.contrib.auth.models import AbstractUser
from multiselectfield import MultiSelectField
from django.utils import timezone # Added for timezone.now
from django.utils.text import slugify # For slug generation if needed, though usually handled in forms/admin

#Create your models here.


DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
)
lis=[0,1,2,3,4,5]

class User(AbstractUser):
    phone_number=models.PositiveIntegerField(default=0)
    is_customer=models.BooleanField(default=False)
    is_broker=models.BooleanField(default=False)
    picture=models.ImageField(upload_to='profile_pics',blank=True)
    def __str__(self):
        return self.username

class Broker(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    department_name=models.CharField(max_length=30)
    location=models.CharField(max_length=30)
    days=MultiSelectField(choices=DAYS_OF_WEEK,blank=True,default=lis)
    average_rating=models.FloatField(blank=True,default=0,null=True)
    experience = models.PositiveIntegerField(null=True, blank=True, help_text="Years of experience")
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills")
    portfolio_link = models.URLField(blank=True, max_length=200)
    # weekdays = weekday_field.fields.WeekdayField()
    def __str__(self):
        return self.user.__str__()


class Customer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    service_providers=models.ManyToManyField(Broker,through='connection')
    def __str__(self):
        return self.user.__str__()

class connection(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="present_customer")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="present_broker")
    description=models.CharField(max_length=150,blank=True)
    customer_status=models.CharField(max_length=30)
    broker_status=models.CharField(max_length=30)
    created_time=models.DateTimeField()
    modified_time=models.DateTimeField()
    is_brokerread=models.BooleanField(default=False)
    is_customerread=models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Failed', 'Failed')],
        default='Pending'
    )
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "From "+self.customer.__str__()+" to "+self.broker.__str__()
choices=(
        (1,'worst'),
        (2,'bad'),
        (3,'average'),
        (4,'good'),
        (5,'excellent'),
    )
class feedback(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="feedback_customer")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="feedback_broker")
    description=models.CharField(max_length=150)
    
    rating=models.IntegerField(choices=choices,default=4)
    created_time=models.DateTimeField()
    def __str__(self):
        return "To "+self.broker.__str__()

class Message(models.Model):
    customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="customer_message")
    broker=models.ForeignKey(Broker,on_delete=models.CASCADE,related_name="broker_message")
    message = models.CharField(max_length=1200)
    timestamp = models.DateTimeField()
    flag=models.BooleanField()
    is_brokerread = models.BooleanField(default=False)
    is_customerread = models.BooleanField(default=False)
    def __str__(self):
        return self.message

    class Meta:
        ordering = ('timestamp',)

class Dispute(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Under Review', 'Under Review'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]
    connection = models.ForeignKey(connection, on_delete=models.CASCADE, related_name='disputes')
    reporter_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_disputes')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dispute for connection {self.connection.id} by {self.reporter_user.username} - Status: {self.status}"

class BlogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name_plural = "Blog Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class BlogPost(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique_for_date='published_date')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts')
    content = models.TextField()
    published_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Draft')

    class Meta:
        ordering = ('-published_date',)
        # unique_together = [['slug', 'published_date']] # Replaced by unique_for_date on slug field

    def __str__(self):
        return self.title

    # Example: Auto-generate slug from title if not provided, can be done in save method
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         self.slug = slugify(self.title)
    #         # Handle potential slug collisions if not using unique_for_date properly
    #     super().save(*args, **kwargs)
