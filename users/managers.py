from django.contrib.auth.base_user import BaseUserManager


from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    
    def create_user(self, email=None, password=None, **extra_fields):

        admission_number = extra_fields.get("admission_number")

        # AUTO EMAIL GENERATION
        if not email:
            if admission_number:
                email = f"{admission_number}@school.local"
            else:
                raise ValueError("Email or admission_number is required")

        email = self.normalize_email(email)

        # SAFETY: remove legacy Django field
        extra_fields.pop("username", None)

        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "superuser")

        if not email:
            raise ValueError("Superuser must have email")

        return self.create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "superuser")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        if not email:
            raise ValueError("Superuser must have email")

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )
