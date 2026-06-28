"""
Promotion Service - Handles student promotion logic
Allows promotion at end of year using class level (1-2-3) then graduation
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from students.models import Student
from classes.models import Class, Stream
from schools.models import StudentPromotion

User = get_user_model()


class PromotionService:
    """Service for handling student promotions at the end of the academic year"""

    @staticmethod
    def get_next_class(current_class, current_stream=None):
        """
        Get the next class for a student based on current class level.
        
        Logic:
        - Level 1 → Level 2 (same school, same stream if exists)
        - Level 2 → Level 3 (same school, same stream if exists)
        - Level 3 → Graduated (remove from classes)
        
        Args:
            current_class: The Class object the student is currently in
            current_stream: The Stream object the student is currently in (optional)
        
        Returns:
            tuple: (next_class, next_stream) or (None, None) if graduated
        """
        if not current_class:
            return None, None

        school = current_class.school
        current_level = current_class.level

        # Graduation logic: if level is 3, student graduates
        if current_level >= 3:
            return None, None  # Student graduated

        # Get next level class
        next_level = current_level + 1
        
        try:
            next_class = Class.objects.get(
                school=school,
                level=next_level
            )
        except Class.DoesNotExist:
            # Create next class if it doesn't exist
            next_class = PromotionService.create_next_class(
                school, 
                current_class, 
                next_level
            )

        # Handle stream promotion (e.g., Grade 10 East → Grade 11 East)
        next_stream = None
        if current_stream:
            # Try to find or create same stream in next class
            next_stream = PromotionService.get_or_create_stream(
                next_class,
                current_stream.name
            )

        return next_class, next_stream

    @staticmethod
    def create_next_class(school, reference_class, next_level):
        """
        Create the next class level if it doesn't exist.
        
        Args:
            school: The School object
            reference_class: The current class to use as reference
            next_level: The level number for the new class
        
        Returns:
            Class: The newly created class
        """
        class_name = reference_class.name.replace(
            str(reference_class.level), 
            str(next_level)
        )
        
        next_class, created = Class.objects.get_or_create(
            school=school,
            level=next_level,
            defaults={
                'name': class_name,
                'class_master': reference_class.class_master  # Optional: carry over class master
            }
        )
        
        return next_class

    @staticmethod
    def get_or_create_stream(class_obj, stream_name):
        """
        Get or create a stream in a class.
        
        Args:
            class_obj: The Class object
            stream_name: The name of the stream (e.g., "A", "East")
        
        Returns:
            Stream: The stream object
        """
        stream, created = Stream.objects.get_or_create(
            class_group=class_obj,
            name=stream_name
        )
        return stream

    @staticmethod
    @transaction.atomic
    def promote_student(student, next_class, next_stream=None, promoted_by=None, remarks=""):
        """
        Promote a single student to the next class.
        
        Args:
            student: Student object to promote
            next_class: The Class to promote to (or None for graduation)
            next_stream: The Stream to promote to (optional)
            promoted_by: User performing the promotion
            remarks: Any additional remarks about the promotion
        
        Returns:
            StudentPromotion: The promotion record created
        """
        current_class = student.current_class
        current_stream = student.stream

        # Create promotion record
        promotion = StudentPromotion.objects.create(
            school=student.school,
            student=student,
            from_class=current_class,
            to_class=next_class,
            from_stream=current_stream,
            to_stream=next_stream,
            status='graduated' if next_class is None else 'promoted',
            remarks=remarks,
            promoted_by=promoted_by
        )

        # Update student's class and stream
        if next_class:
            student.current_class = next_class
            student.stream = next_stream
            student.status = 'active'
        else:
            # Student graduated
            student.current_class = None
            student.stream = None
            student.status = 'inactive'

        student.save()

        return promotion

    @staticmethod
    @transaction.atomic
    def promote_class(class_obj, promoted_by=None):
        """
        Promote all students in a class to the next level.
        
        Args:
            class_obj: The Class object to promote
            promoted_by: User performing the promotion
        
        Returns:
            dict: Statistics of the promotion operation
        """
        students = Student.objects.filter(
            current_class=class_obj,
            status='active'
        )

        promoted_count = 0
        graduated_count = 0
        failed_count = 0
        promotions = []

        for student in students:
            try:
                next_class, next_stream = PromotionService.get_next_class(
                    class_obj, 
                    student.stream
                )

                promotion = PromotionService.promote_student(
                    student,
                    next_class,
                    next_stream,
                    promoted_by=promoted_by
                )
                promotions.append(promotion)

                if next_class is None:
                    graduated_count += 1
                else:
                    promoted_count += 1

            except Exception as e:
                failed_count += 1
                # Log error or handle as needed

        return {
            'total': len(students),
            'promoted': promoted_count,
            'graduated': graduated_count,
            'failed': failed_count,
            'promotions': promotions
        }

    @staticmethod
    @transaction.atomic
    def promote_stream(stream_obj, promoted_by=None):
        """
        Promote all students in a specific stream.
        
        Args:
            stream_obj: The Stream object to promote
            promoted_by: User performing the promotion
        
        Returns:
            dict: Statistics of the promotion operation
        """
        students = Student.objects.filter(
            stream=stream_obj,
            status='active'
        )

        promoted_count = 0
        graduated_count = 0
        failed_count = 0
        promotions = []

        for student in students:
            try:
                next_class, next_stream = PromotionService.get_next_class(
                    student.current_class,
                    stream_obj
                )

                promotion = PromotionService.promote_student(
                    student,
                    next_class,
                    next_stream,
                    promoted_by=promoted_by
                )
                promotions.append(promotion)

                if next_class is None:
                    graduated_count += 1
                else:
                    promoted_count += 1

            except Exception as e:
                failed_count += 1

        return {
            'total': len(students),
            'promoted': promoted_count,
            'graduated': graduated_count,
            'failed': failed_count,
            'promotions': promotions
        }

    @staticmethod
    @transaction.atomic
    def promote_school(school, promoted_by=None):
        """
        Promote all students in a school.
        
        Args:
            school: The School object
            promoted_by: User performing the promotion
        
        Returns:
            dict: Statistics of the promotion operation
        """
        classes = Class.objects.filter(school=school)

        total_promoted = 0
        total_graduated = 0
        total_failed = 0
        all_promotions = []

        for class_obj in classes:
            stats = PromotionService.promote_class(class_obj, promoted_by=promoted_by)
            total_promoted += stats['promoted']
            total_graduated += stats['graduated']
            total_failed += stats['failed']
            all_promotions.extend(stats['promotions'])

        return {
            'total_students': total_promoted + total_graduated + total_failed,
            'promoted': total_promoted,
            'graduated': total_graduated,
            'failed': total_failed,
            'promotions': all_promotions
        }

    @staticmethod
    def repeat_student(student, repeated_by=None, remarks=""):
        """
        Keep a student in the same class (repeat the year).
        
        Args:
            student: Student object
            repeated_by: User performing the action
            remarks: Reason for repetition
        
        Returns:
            StudentPromotion: The promotion record created
        """
        promotion = StudentPromotion.objects.create(
            school=student.school,
            student=student,
            from_class=student.current_class,
            to_class=student.current_class,  # Same class
            from_stream=student.stream,
            to_stream=student.stream,  # Same stream
            status='repeated',
            remarks=remarks,
            promoted_by=repeated_by
        )
        # Student stays in same class, no update to student.current_class needed
        return promotion

    @staticmethod
    def drop_student(student, dropped_by=None, remarks=""):
        """
        Drop a student from school.
        
        Args:
            student: Student object
            dropped_by: User performing the action
            remarks: Reason for dropping
        
        Returns:
            StudentPromotion: The promotion record created
        """
        promotion = StudentPromotion.objects.create(
            school=student.school,
            student=student,
            from_class=student.current_class,
            to_class=None,
            from_stream=student.stream,
            to_stream=None,
            status='dropped',
            remarks=remarks,
            promoted_by=dropped_by
        )
        
        student.status = 'inactive'
        student.current_class = None
        student.stream = None
        student.save()
        
        return promotion
