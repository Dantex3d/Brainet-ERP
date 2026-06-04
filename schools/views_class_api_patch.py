from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Class
from classes.models import Stream
from subjects.models import ClassSubject


def class_details_json(request, class_id):
    school = request.user.school
    school_class = get_object_or_404(Class, id=class_id, school=school)

    streams = list(Stream.objects.filter(class_group=school_class).values('id', 'name'))
    assigned_subjects = list(ClassSubject.objects.filter(class_name=school_class).select_related('subject')
                             .values('id', 'subject__id', 'subject__name'))

    data = {
        'class_id': school_class.id,
        'name': school_class.name,
        'level': school_class.level,
        'class_master_id': school_class.class_master_id,
        'streams': streams,
        'assigned_subjects': assigned_subjects,
    }

    return JsonResponse(data)
