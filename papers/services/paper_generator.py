from collections import defaultdict
from papers.models import Question


def calculate_bloom_target_marks(total_marks, bloom_distribution):
    targets = {}

    for bloom_level, percent in bloom_distribution.items():
        targets[bloom_level] = round((percent / 100) * total_marks)

    difference = total_marks - sum(targets.values())

    if difference != 0:
        largest_key = max(bloom_distribution, key=bloom_distribution.get)
        targets[largest_key] += difference

    return targets


def pick_questions_for_target(questions, target_marks, target_count, selected_ids):
    selected = []
    current_marks = 0

    for question in questions:
        if question.id in selected_ids:
            continue

        if len(selected) >= target_count:
            break

        if current_marks + question.marks <= target_marks:
            selected.append(question)
            selected_ids.add(question.id)
            current_marks += question.marks

        if current_marks == target_marks and len(selected) == target_count:
            break

    return selected, current_marks


def calculate_bloom_question_targets(number_of_questions, bloom_distribution):
    targets = {}

    for bloom_level, percent in bloom_distribution.items():
        targets[bloom_level] = round((percent / 100) * number_of_questions)

    difference = number_of_questions - sum(targets.values())

    if difference != 0:
        largest_key = max(bloom_distribution, key=bloom_distribution.get)
        targets[largest_key] += difference

    return targets


def fill_remaining_requirements(
    questions,
    remaining_marks,
    remaining_count,
    selected_ids
):
    selected = []
    current_marks = 0

    for question in questions:
        if question.id in selected_ids:
            continue

        if len(selected) >= remaining_count:
            break

        if current_marks + question.marks <= remaining_marks:
            selected.append(question)
            selected_ids.add(question.id)
            current_marks += question.marks

        if current_marks == remaining_marks and len(selected) == remaining_count:
            break

    return selected, current_marks


def generate_blueprint_paper(
    user,
    subject,
    total_marks,
    number_of_questions,
    topics=None,
    bloom_distribution=None,
):
    base_questions = Question.objects.filter(
        created_by=user,
        subject=subject
    )

    if topics:
        base_questions = base_questions.filter(topic__in=topics)

    base_questions = base_questions.order_by("times_used", "?")

    bloom_distribution = bloom_distribution or {}

    bloom_mark_targets = calculate_bloom_target_marks(
        total_marks=total_marks,
        bloom_distribution=bloom_distribution
    )

    bloom_question_targets = calculate_bloom_question_targets(
        number_of_questions=number_of_questions,
        bloom_distribution=bloom_distribution
    )

    selected_questions = []
    selected_ids = set()
    achieved_marks = 0
    bloom_achieved = defaultdict(int)
    bloom_question_achieved = defaultdict(int)

    # Phase 1: Try to satisfy Bloom targets by both marks and question count
    for bloom_level, target_marks in bloom_mark_targets.items():
        target_count = bloom_question_targets.get(bloom_level, 0)

        if target_marks <= 0 or target_count <= 0:
            continue

        questions = list(
            base_questions.filter(bloom_level=bloom_level)
        )

        picked, picked_marks = pick_questions_for_target(
            questions=questions,
            target_marks=target_marks,
            target_count=target_count,
            selected_ids=selected_ids
        )

        selected_questions.extend(picked)
        achieved_marks += picked_marks
        bloom_achieved[bloom_level] += picked_marks
        bloom_question_achieved[bloom_level] += len(picked)

    # Phase 2: Fill remaining marks and remaining question count with any unused questions
    remaining_marks = total_marks - achieved_marks
    remaining_count = number_of_questions - len(selected_questions)

    if remaining_marks > 0 and remaining_count > 0:
        questions = list(base_questions)

        picked, picked_marks = fill_remaining_requirements(
            questions=questions,
            remaining_marks=remaining_marks,
            remaining_count=remaining_count,
            selected_ids=selected_ids
        )

        selected_questions.extend(picked)
        achieved_marks += picked_marks

        for question in picked:
            bloom_achieved[question.bloom_level] += question.marks
            bloom_question_achieved[question.bloom_level] += 1

    return {
        "selected_questions": selected_questions,
        "achieved_marks": achieved_marks,
        "achieved_count": len(selected_questions),
        "bloom_mark_targets": dict(bloom_mark_targets),
        "bloom_question_targets": dict(bloom_question_targets),
        "bloom_achieved": dict(bloom_achieved),
        "bloom_question_achieved": dict(bloom_question_achieved),
    }