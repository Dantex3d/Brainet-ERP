"""
Management command to backfill subject enrollments for existing students
"""
from django.core.management.base import BaseCommand
from students.models import Student
from subjects.models import ClassSubject, StudentSubject


class Command(BaseCommand):
    help = 'Backfill student subject enrollments from ClassSubject assignments'

    def handle(self, *args, **options):
        """
        For each student, create StudentSubject entries based on the ClassSubjects
        assigned to their current class.
        """
        
        students = Student.objects.filter(status='active').select_related('current_class')
        created_count = 0
        skipped_count = 0
        
        for student in students:
            if not student.current_class:
                skipped_count += 1
                continue
            
            # Get all ClassSubjects for this student's class
            class_subjects = ClassSubject.objects.filter(
                class_name=student.current_class,
                school=student.school
            )
            
            for cs in class_subjects:
                # Create StudentSubject entry if it doesn't exist
                obj, created = StudentSubject.objects.get_or_create(
                    student=student,
                    subject=cs.subject,
                    defaults={'class_subject': cs}
                )
                
                if created:
                    created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} student-subject enrollments. '
                f'Skipped {skipped_count} students without class assignments.'
            )
        )
