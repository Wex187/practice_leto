import requests
import psycopg2
from flask import Flask, request, render_template, redirect, url_for
import re
import os

app = Flask(__name__)

# Получение списка регионов и городов
response = requests.get('https://api.hh.ru/areas')
areas = response.json()


def connect_db():
    return psycopg2.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        user="postgres",
        password="12365477S",
        database="vac",
    )


def get_city_id(city_name, areas):
    city_name_lower = city_name.strip().lower()
    for country in areas:
        for area in country['areas']:
            if area['name'].strip().lower() == city_name_lower:
                return area['id']
            if 'areas' in area:
                for city in area['areas']:
                    if city['name'].strip().lower() == city_name_lower:
                        return city['id']
                    for sub_area in city['areas']:
                        if sub_area['name'].strip().lower() == city_name_lower:
                            return sub_area['id']
    return None


def parse(area, keyword, per_page=50):
    url = 'https://api.hh.ru/vacancies'
    params = {
        'area': area,
        'text': keyword,
        'per_page': per_page
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f'Не удалось получить данные: {response.status_code}')
        return []

    data = response.json()
    vacancies = []
    for item in data['items']:
        title = item['name']
        link = item['alternate_url']
        company = item['employer']['name']
        area = item['area']['name']
        salary_info = item['salary']

        if salary_info is None:
            salary = "Заработная плата не указана"
        else:
            salary_from = salary_info.get('from')
            salary_to = salary_info.get('to')
            salary_currency = salary_info.get('currency')
            salary_gross = salary_info.get('gross')

            salary = ''
            if salary_from:
                salary += f"от {salary_from} "
            if salary_to:
                salary += f"до {salary_to} "
            if salary_currency:
                salary += salary_currency
            if salary_gross:
                salary += " до вычета налогов" if salary_gross else " после вычета налогов"

        experience_required = item.get('experience', {}).get('name', 'Не указан')

        vacancies.append({
            'title': title,
            'link': link,
            'company': company,
            'area': area,
            'salary': salary.strip(),
            'experience_required': experience_required
        })

    return vacancies


def save_to_db(vacancies):
    conn = connect_db()
    cursor = conn.cursor()

    for vacancy in vacancies:
        cursor.execute("""
            INSERT INTO vacancies (title, link, company, area, salary, experience_required)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (link) DO NOTHING;
        """, (vacancy['title'], vacancy['link'], vacancy['company'], vacancy['area'], vacancy['salary'],
              vacancy['experience_required']))

    conn.commit()
    cursor.close()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        city = request.form.get('city')

        city_id = get_city_id(city, areas)

        if city_id:
            vacancies = parse(city_id, keyword)
            if vacancies:
                save_to_db(vacancies)
                return redirect(url_for('results'))
            else:
                return "Вакансий не найдено"
        else:
            return f'Город {city} не найден'

    return render_template('index.html')


@app.route('/results', methods=['GET'])
def results():
    conn = connect_db()
    cursor = conn.cursor()

    query = "SELECT title, link, company, area, salary, experience_required FROM vacancies WHERE 1=1"
    filters = []

    title = request.args.get('title')
    company = request.args.get('company')
    area = request.args.get('area')
    experience_required = request.args.get('experience_mode')

    salary_filter = request.args.get('salary_filter')

    if salary_filter == 'with_salary':
        query += " AND salary != 'Заработная плата не указана'"
    elif salary_filter == 'without_salary':
        query += " AND salary = 'Заработная плата не указана'"
    # Добавим вариант для выбора всех вакансий, включая те, где зарплата не указана
    elif salary_filter == 'all':
        pass  # Не добавляем никаких дополнительных условий

    if title:
        query += " AND title ILIKE %s"
        filters.append(f"%{title}%")
    if company:
        query += " AND company ILIKE %s"
        filters.append(f"%{company}%")
    if area:
        query += " AND area ILIKE %s"
        filters.append(f"%{area}%")
    if experience_required and experience_required != 'all':
        if experience_required == 'no_experience':
            query += " AND experience_required = 'Нет опыта'"
        elif experience_required == 'some_experience':
            query += " AND experience_required != 'Нет опыта'"

    cursor.execute(query, tuple(filters))
    vacancies = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('results.html', vacancies=vacancies)


if __name__ == '__main__':
    app.run(debug=True)






