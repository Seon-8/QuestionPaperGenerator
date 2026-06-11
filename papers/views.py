from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Subject, Topic, Question, GeneratedPaper, PaperQuestion
from .forms import SubjectForm, TopicForm, QuestionForm, GeneratePaperForm
from .services.paper_generator import generate_blueprint_paper
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .forms import AIQuestionGenerateForm
from .services.ai_service import generate_questions_with_ai
from .services.ai_service import generate_missing_questions_with_ai
from django.contrib import messages
from django.http import JsonResponse


@login_required
def dashboard(request):
    context = {
        "subject_count": Subject.objects.filter(created_by=request.user).count(),
        "question_count": Question.objects.filter(created_by=request.user).count(),
        "paper_count": GeneratedPaper.objects.filter(created_by=request.user).count(),
    }
    return render(request, "papers/dashboard.html", context)


@login_required
def subject_list(request):
    subjects = Subject.objects.filter(created_by=request.user)
    return render(request, "papers/subject_list.html", {"subjects": subjects})


@login_required
def add_subject(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.created_by = request.user
            subject.save()
            return redirect("subject_list")
    else:
        form = SubjectForm()

    return render(request, "papers/form.html", {"form": form, "title": "Add Subject"})


@login_required
def add_topic(request):
    if request.method == "POST":
        form = TopicForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("subject_list")
    else:
        form = TopicForm()

    return render(request, "papers/form.html", {"form": form, "title": "Add Topic"})


@login_required
def question_list(request):
    questions = Question.objects.filter(created_by=request.user)

    difficulty = request.GET.get("difficulty")
    if difficulty:
        questions = questions.filter(difficulty=difficulty)

    bloom_level = request.GET.get("bloom_level")
    if bloom_level:
        questions = questions.filter(bloom_level=bloom_level)

    return render(request, "papers/question_list.html", {"questions": questions})


@login_required
def add_question(request):
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            return redirect("question_list")
    else:
        form = QuestionForm()

    return render(request, "papers/form.html", {"form": form, "title": "Add Question"})

def sort_questions_for_paper(questions):

    return sorted(
        questions,
        key=lambda q: (
            q.marks,
            q.bloom_level,
            q.id
        )
    )

@login_required
def load_topics(request):
    subject_id = request.GET.get("subject_id")

    topics = Topic.objects.filter(
        subject_id=subject_id,
        subject__created_by=request.user
    ).order_by("name")

    topic_list = []

    for topic in topics:
        topic_list.append({
            "id": topic.id,
            "name": topic.name
        })

    return JsonResponse({
        "topics": topic_list
    })

@login_required
def generate_paper(request):
    if request.method == "POST":
        form = GeneratePaperForm(request.user, request.POST)

        if form.is_valid():
            title = form.cleaned_data["title"]
            subject = form.cleaned_data["subject"]
            topics = form.cleaned_data["topics"]
            total_marks = form.cleaned_data["total_marks"]
            number_of_questions = form.cleaned_data["number_of_questions"]
            duration_minutes = form.cleaned_data["duration_minutes"]
            use_ai_fill = form.cleaned_data["use_ai_fill"]

            bloom_distribution = {
                "remember": form.cleaned_data["remember_percent"],
                "understand": form.cleaned_data["understand_percent"],
                "apply": form.cleaned_data["apply_percent"],
                "analyze": form.cleaned_data["analyze_percent"],
                "evaluate": form.cleaned_data["evaluate_percent"],
                "create": form.cleaned_data["create_percent"],
            }


            result = generate_blueprint_paper(
                user=request.user,
                subject=subject,
                topics=topics,
                total_marks=total_marks,
                number_of_questions=number_of_questions,
                bloom_distribution=bloom_distribution,
            )

            selected_questions = result["selected_questions"]
            achieved_marks = result["achieved_marks"]

            ai_generated_count = 0

            if (achieved_marks != total_marks or len(selected_questions) != number_of_questions) and use_ai_fill:
                missing_marks = total_marks - achieved_marks
                missing_count = number_of_questions - len(selected_questions)

                if missing_marks > 0 and missing_count == 0 and selected_questions:
                    question_to_replace = selected_questions[-1]

                    selected_questions.remove(question_to_replace)
                    achieved_marks -= question_to_replace.marks

                    missing_marks = total_marks - achieved_marks
                    missing_count = number_of_questions - len(selected_questions)

                if missing_marks == 0 and missing_count > 0 and selected_questions:
                    question_to_replace = selected_questions[-1]

                    selected_questions.remove(question_to_replace)
                    achieved_marks -= question_to_replace.marks

                    missing_marks = total_marks - achieved_marks
                    missing_count = number_of_questions - len(selected_questions)

                if missing_marks <= 0 or missing_count <= 0:
                    return render(request, "papers/generate_paper.html", {
                        "form": form,
                        "error": (
                            f"Could not balance exactly {total_marks} marks with "
                            f"{number_of_questions} questions. Try changing the total marks, "
                            f"number of questions, or question bank."
                        )
                    })

                selected_topics = list(topics)

                if not selected_topics:
                    return render(request, "papers/generate_paper.html", {
                        "form": form,
                        "error": "Please select at least one topic when using AI fill missing questions."
                    })

                ai_topic = selected_topics[0]
                ai_bloom_level = max(bloom_distribution, key=bloom_distribution.get)
                ai_difficulty = "medium"

                ai_questions = generate_missing_questions_with_ai(
                    subject=subject.name,
                    topic=ai_topic.name,
                    difficulty=ai_difficulty,
                    bloom_level=ai_bloom_level,
                    missing_marks=missing_marks,
                    missing_count=missing_count
                )

                for item in ai_questions:
                    question_text = item.get("question_text", "").strip()

                    if not question_text:
                        continue

                    new_question = Question.objects.create(
                        created_by=request.user,
                        subject=subject,
                        topic=ai_topic,
                        question_text=question_text,
                        expected_answer=item.get("expected_answer", "").strip(),
                        marks=item.get("marks", 1),
                        difficulty=ai_difficulty,
                        bloom_level=ai_bloom_level,
                        is_ai_generated=True
                    )

                    selected_questions.append(new_question)
                    achieved_marks += new_question.marks
                    ai_generated_count += 1

            achieved_count = len(selected_questions)

            if achieved_marks != total_marks or achieved_count != number_of_questions:
                return render(request, "papers/generate_paper.html", {
                    "form": form,
                    "error": (
                        f"Could only generate {achieved_count} question(s) and "
                        f"{achieved_marks} marks out of requested "
                        f"{number_of_questions} question(s) and {total_marks} marks. "
                        f"Add more questions or enable AI fill."
                    )
                })

            selected_questions = sort_questions_for_paper(selected_questions)
            paper = GeneratedPaper.objects.create(
                created_by=request.user,
                subject=subject,
                title=title,
                total_marks=total_marks,
                duration_minutes=duration_minutes
            )

            for index, question in enumerate(selected_questions, start=1):
                PaperQuestion.objects.create(
                    paper=paper,
                    question=question,
                    order=index
                )

                question.times_used += 1
                question.save()

            if ai_generated_count > 0:
                messages.success(
                    request,
                    f"AI generated {ai_generated_count} missing question(s) to complete the paper."
                )

            messages.success(
                request,
                "Question paper generated successfully using Bloom percentage distribution"
            )

            return redirect("paper_preview", paper_id=paper.id)

    else:
        form = GeneratePaperForm(request.user)

    return render(request, "papers/generate_paper.html", {"form": form})

@login_required
def paper_preview(request, paper_id):
    paper = get_object_or_404(
        GeneratedPaper,
        id=paper_id,
        created_by=request.user
    )

    paper_questions = PaperQuestion.objects.filter(paper=paper).order_by("order")

    return render(request, "papers/paper_preview.html", {
        "paper": paper,
        "paper_questions": paper_questions
    })

@login_required
def paper_list(request):
    papers = GeneratedPaper.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    return render(request, "papers/paper_list.html", {
        "papers": papers
    })

@login_required
def ai_generate_questions(request):
    if request.method == "POST":
        form = AIQuestionGenerateForm(request.user, request.POST)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            topic = form.cleaned_data["topic"]
            difficulty = form.cleaned_data["difficulty"]
            bloom_level = form.cleaned_data["bloom_level"]
            marks = form.cleaned_data["marks"]
            count = form.cleaned_data["count"]

            ai_questions = generate_questions_with_ai(
                subject=subject.name,
                topic=topic.name,
                difficulty=difficulty,
                bloom_level=bloom_level,
                marks=marks,
                count=count
            )

            for item in ai_questions:
                Question.objects.create(
                    created_by=request.user,
                    subject=subject,
                    topic=topic,
                    question_text=item.get("question_text", ""),
                    expected_answer=item.get("expected_answer", ""),
                    marks=item.get("marks", marks),
                    difficulty=item.get("difficulty", difficulty),
                    bloom_level=item.get("bloom_level", bloom_level),
                    is_ai_generated=True
                )

            return redirect("question_list")

    else:
        form = AIQuestionGenerateForm(request.user)

    return render(request, "papers/form.html", {
        "form": form,
        "title": "Generate Questions with AI"
    })


def draw_wrapped_text(p, text, x, y, max_width, font_name="Helvetica", font_size=11, line_height=16):
    p.setFont(font_name, font_size)

    paragraphs = text.split("\n")

    for paragraph in paragraphs:
        words = paragraph.split()
        line = ""

        for word in words:
            test_line = line + word + " "

            if p.stringWidth(test_line, font_name, font_size) <= max_width:
                line = test_line
            else:
                p.drawString(x, y, line)
                y -= line_height
                line = word + " "

        if line:
            p.drawString(x, y, line)
            y -= line_height

        y -= 5

    return y

@login_required
def download_paper_pdf(request, paper_id):
    paper = get_object_or_404(
        GeneratedPaper,
        id=paper_id,
        created_by=request.user
    )

    paper_questions = PaperQuestion.objects.filter(paper=paper).order_by("order")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{paper.title}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, paper.title)

    y -= 30
    p.setFont("Helvetica", 11)
    p.drawCentredString(width / 2, y, f"Subject: {paper.subject.name}")

    y -= 20
    p.drawCentredString(
        width / 2,
        y,
        f"Total Marks: {paper.total_marks} | Time: {paper.duration_minutes} minutes"
    )

    y -= 40
    p.line(50, y, width - 50, y)

    y -= 30
    p.setFont("Helvetica", 11)

    for item in paper_questions:
        question_text = (f"Q{item.order}. {item.question.question_text} "f"[{item.question.marks} marks | "f"Bloom: {item.question.get_bloom_level_display()}]")

        y = draw_wrapped_text(p=p,text=question_text,x=50,y=y,max_width=width-100,font_name="Helvetica",font_size=11,line_height=16)

        y-=10

        if y < 70:
            p.showPage()
            p.setFont("Helvetica", 11)
            y = height - 50

    p.showPage()
    p.save()

    return response


@login_required
def download_answer_key_pdf(request, paper_id):
    paper = get_object_or_404(
        GeneratedPaper,
        id=paper_id,
        created_by=request.user
    )

    paper_questions = PaperQuestion.objects.filter(paper=paper).order_by("order")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{paper.title}_answer_key.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, f"{paper.title} - Answer Key")

    y -= 30
    p.setFont("Helvetica", 11)
    p.drawCentredString(width / 2, y, f"Subject: {paper.subject.name}")

    y -= 20
    p.drawCentredString(
        width / 2,
        y,
        f"Total Marks: {paper.total_marks} | Time: {paper.duration_minutes} minutes"
    )

    y -= 40
    p.line(50, y, width - 50, y)

    y -= 30

    for item in paper_questions:
        question = item.question

        answer_text = question.expected_answer

        if not answer_text:
            answer_text = "No answer provided."

        full_text = (f"Q{item.order}. {question.question_text} "f"[{question.marks} marks | "f"Topic: {question.topic.name} | "f"Bloom: {question.get_bloom_level_display()}]\n" f"Answer: {answer_text}")

        y = draw_wrapped_text(
            p=p,
            text=full_text,
            x=50,
            y=y,
            max_width=width - 100,
            font_name="Helvetica",
            font_size=11,
            line_height=16
        )

        y -= 15

        if y < 70:
            p.showPage()
            p.setFont("Helvetica", 11)
            y = height - 50

    p.showPage()
    p.save()

    return response


