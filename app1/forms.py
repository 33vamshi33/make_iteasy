from django import forms
from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User # User is already imported from app1.models
from app1.models import User,Customer,Broker,connection,feedback, BlogCategory, BlogPost # Added BlogCategory, BlogPost

class userform(UserCreationForm):
    class Meta():
        model=User
        fields=('username','email',"phone_number")

class loginform(forms.ModelForm):
    class Meta():
        fields=('username','password')
class brokerform(forms.ModelForm):

    class Meta():
        model=Broker
        fields=('department_name','location','days', 'experience', 'skills', 'portfolio_link')

class searchform(forms.ModelForm):
    
    class Meta():
        model=Broker
        fields=('department_name','location','days')


class userprofileform(forms.ModelForm):
    class Meta():
        model=User
        fields=('picture',)

class feedbackform(forms.ModelForm):
    class Meta():
        model=feedback
        fields=("rating","description")

class DisputeForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please describe the issue in detail.'}), required=True)

class BlogPostForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=BlogCategory.objects.all(), required=False, empty_label="Select a category")
    published_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Set a specific publication date and time, or leave for now to publish immediately."
    )

    class Meta:
        model = BlogPost
        fields = ['title', 'slug', 'category', 'content', 'status', 'published_date']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }
        help_texts = {
            'slug': 'A unique-for-date identifier for the URL (e.g., "my-first-post"). Will be auto-generated if left blank, but ensure it is unique for the chosen published date.',
            'status': 'Set to "Published" to make the post publicly visible.',
        }