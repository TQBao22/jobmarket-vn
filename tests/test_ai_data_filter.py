from jobmarket.crawl.itviec import is_ai_data


def job(title, description="", tags=None):
    return {"title": title, "description": description, "tags": tags or []}


def test_title_with_ai_data_role_is_kept():
    assert is_ai_data(job("Senior Data Engineer"))
    assert is_ai_data(job("Machine Learning Engineer (Python)"))
    assert is_ai_data(job("Chuyên viên phân tích dữ liệu"))


def test_vietnamese_model_building_title_is_kept():
    # slug-only filter missed this real ITviec job
    assert is_ai_data(job("CV/CVCC Xây dựng mô hình phát hiện gian lận"))


def test_generic_dev_job_mentioning_ai_tools_is_dropped():
    desc = "Build REST APIs in Java. Use AI coding assistants such as GitHub Copilot daily. LLM experience is a plus."
    assert not is_ai_data(job("Senior Java Developer", desc))


def test_business_analyst_without_ml_content_is_dropped():
    assert not is_ai_data(job("Business Analyst (Banking)", "Write BRD and user stories, SQL basic."))


def test_unaccented_vietnamese_title_is_kept():
    # ITviec titles often drop diacritics
    assert is_ai_data(job("CV, CVCC Xay Dung Mo Hinh Phat Hien Gian Lan"))


def test_backend_job_whose_description_mentions_data_tools_is_dropped():
    # role comes from the title; ETL/Airflow in a backend JD does not make it an AI/Data job
    desc = "Maintain ETL jobs on Airflow, feed the data warehouse, support machine learning team."
    assert not is_ai_data(job("Mid/Sen Backend Developer Java/Spring Boot/SQL/Kafka", desc))


def test_word_boundaries_avoid_false_hits():
    # "ai" inside words, "bi" inside words must not match
    assert not is_ai_data(job("Mobile Developer (Kotlin) - Thái Bình, Bình Dương", "Maintain Android apps."))
