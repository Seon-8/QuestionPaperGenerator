from django import forms
from .models import Subject, Topic, Question

def add_bootstrap_classes(form):
    for field_name, field in form.fields.items():
        existing_classes = field.widget.attrs.get("class", "")

        if field.widget.__class__.__name__ == "CheckboxInput":
            field.widget.attrs["class"] = existing_classes + " form-check-input"
        elif field.widget.__class__.__name__ == "CheckboxSelectMultiple":
            field.widget.attrs["class"] = existing_classes
        else:
            field.widget.attrs["class"] = existing_classes + " form-control"

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["subject", "name"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            "subject",
            "topic",
            "question_text",
            "expected_answer",
            "marks",
            "difficulty",
            "bloom_level",
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class GeneratePaperForm(forms.Form):
    title = forms.CharField(max_length=200)

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none()
    )

    topics = forms.ModelMultipleChoiceField(
    queryset=Topic.objects.none(),
    required=False,
    widget=forms.CheckboxSelectMultiple,
    label="Select Topics"
    )

    total_marks = forms.IntegerField(min_value=1)
    number_of_questions = forms.IntegerField(
    min_value=1,
    initial=10,
    label="Number of Questions"
    )
    duration_minutes = forms.IntegerField(min_value=1, initial=120)

    # Bloom percentage fields
    remember_percent = forms.IntegerField(min_value=0, max_value=100, initial=10)
    understand_percent = forms.IntegerField(min_value=0, max_value=100, initial=30)
    apply_percent = forms.IntegerField(min_value=0, max_value=100, initial=20)
    analyze_percent = forms.IntegerField(min_value=0, max_value=100, initial=20)
    evaluate_percent = forms.IntegerField(min_value=0, max_value=100, initial=20)
    create_percent = forms.IntegerField(min_value=0, max_value=100, initial=0)

    use_ai_fill = forms.BooleanField(
        required=False,
        label="Use AI to fill missing marks if question bank is insufficient"
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields["subject"].queryset = Subject.objects.filter(created_by=user)
        self.fields["topics"].queryset = Topic.objects.none()

        if "subject" in self.data:
            try:
                subject_id = int(self.data.get("subject"))
                self.fields["topics"].queryset = Topic.objects.filter(
                    subject_id=subject_id,
                    subject__created_by=user
                ).order_by("name")
            except (ValueError, TypeError):
                pass


    def clean(self):
        cleaned_data = super().clean()

        bloom_total = (
            cleaned_data.get("remember_percent", 0)
            + cleaned_data.get("understand_percent", 0)
            + cleaned_data.get("apply_percent", 0)
            + cleaned_data.get("analyze_percent", 0)
            + cleaned_data.get("evaluate_percent", 0)
            + cleaned_data.get("create_percent", 0)
        )

        if bloom_total != 100:
            raise forms.ValidationError("Bloom percentages must add up to 100.")

        return cleaned_data

class AIQuestionGenerateForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.none())
    topic = forms.ModelChoiceField(queryset=Topic.objects.none())

    difficulty = forms.ChoiceField(choices=Question.DIFFICULTY_CHOICES)
    bloom_level = forms.ChoiceField(choices=Question.BLOOM_CHOICES)

    marks = forms.IntegerField(min_value=1)
    count = forms.IntegerField(min_value=1, max_value=10)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)
        self.fields["subject"].queryset = Subject.objects.filter(created_by=user)
        self.fields["topic"].queryset = Topic.objects.filter(subject__created_by=user)