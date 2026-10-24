# Sanghi

A Django web application for creating and downloading customized business marketing posters, banners, and promotional designs.

## Features

- Poster Generation: Generate custom posters and banners using templates or AI prompts.
- Brand Kit: Save business details, contact information, logos, and brand colors to apply to designs.
- Template Management: Browse and manage template categories for different business types and events.
- Admin Dashboard: Manage users, categories, templates, subscriptions, and platform activity.
- User Dashboard: View saved designs, update profile information, and manage subscription credits.
- Authentication: User login and registration with mobile verification.

## Tech Stack

- Python and Django
- Django REST Framework
- SQLite (Development)
- Pillow
- HTML, CSS, JavaScript

## Setup Instructions

1. Clone the repository:
   git clone https://github.com/nishalpandit/sanghi.git
   cd sanghi

2. Create and activate a virtual environment:
   python -m venv env
   .\env\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Set up environment variables:
   Copy .env.example to .env and configure your keys if using OpenAI generation.

5. Apply migrations:
   python manage.py migrate

6. Run the local development server:
   python manage.py runserver
