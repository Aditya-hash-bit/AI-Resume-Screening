import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Basic skill list
SKILLS = [
    "python", "machine learning", "flask",
    "sql", "aws", "deep learning", "data analysis"
]

def extract_skills(text):
    found = []
    for skill in SKILLS:
        if skill in text:
            found.append(skill)
    return found


def rank_resumes(resumes, job_description):
    documents = resumes + [job_description]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(documents)

    jd_vector = tfidf_matrix[-1]

    scores = []

    for i in range(len(resumes)):
        resume_vector = tfidf_matrix[i]
        similarity = cosine_similarity(resume_vector, jd_vector)[0][0]

        # Skill matching
        resume_skills = extract_skills(resumes[i])
        jd_skills = extract_skills(job_description)

        skill_score = len(set(resume_skills) & set(jd_skills)) / (len(jd_skills) + 1)

        final_score = (0.7 * similarity) + (0.3 * skill_score)

        scores.append(round(final_score, 3))

    return scores