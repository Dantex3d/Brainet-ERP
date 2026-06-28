# schools/decorators.py

from django.shortcuts import redirect
from django.contrib import messages

def school_active_required(view_func):

    def wrapper(request, *args, **kwargs):

        school = getattr(request.user, "school", None)

        if school and not school.is_active:

            messages.error(
                request,
                "School account is inactive."
            )

            return redirect("logout")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper