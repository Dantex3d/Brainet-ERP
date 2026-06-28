from django import forms
from .models import Teacher

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ["name", "email", "phone", "role", "school"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Hide school field for non-superusers
        if user and not user.is_superuser:
            self.fields.pop("school")
