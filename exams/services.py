from .models import StudentMark, GradingPolicy
from schools.models import ClassSubject


def calculate_grade_and_points(school, score):
    """
    Convert marks into grade using GradingPolicy
    """

    policy = GradingPolicy.objects.filter(
        school=school,
        min_score__lte=score,
        max_score__gte=score
    ).first()

    if not policy:
        return "", 0

    return policy.grade_letter, policy.points


def create_or_update_mark(student, class_subject, term, marks):
    """
    Core mark entry logic (SAFE + REUSABLE)
    """

    grade, points = calculate_grade_and_points(
        class_subject.school,
        marks
    )

    obj, created = StudentMark.objects.update_or_create(
        student=student,
        class_subject=class_subject,
        term=term,
        defaults={
            "marks": marks,
            "grade": grade,
            "points": points
        }
    )

    return obj, created