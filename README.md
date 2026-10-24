# Sanghi - AI-Powered Poster & Digital Branding Platform

An enterprise-ready web platform built with **Django** and **Django REST Framework** that empowers businesses and individuals to generate custom marketing posters, social media banners, and flex designs using AI, customizable templates, and personal brand kits.

---

## 🚀 Key Features

- **🎨 AI-Powered Poster Generation**: Automated visual creation powered by AI image models with automated branding overlay.
- **🏷️ Brand Kit Management**: Store and maintain business logos, brand palettes, contact details, and custom typography across all designs.
- **📁 Multi-Category Template Catalog**: Dynamic template library categorized by business types (Retail, Healthcare, Tech, Real Estate, Food, Events, etc.).
- **📊 Admin & Master Dashboard**: Centralized management for categories, trending designs, cities, business types, subscriptions, and platform analytics.
- **💳 Subscription & Credit System**: Tiered subscription plans with credit tracking and transaction management.
- **🔐 Secure Authentication**: Mobile OTP-based authentication, JWT-supported endpoints, and role-based access control.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Django 6.0, Django REST Framework, SimpleJWT
- **Image Processing**: Pillow (PIL), Requests, OpenAI Image API integration
- **Frontend**: Django Templates, Vanilla CSS & Modern JS (Admin & User Dashboards, Web Portal)
- **Database**: SQLite (default for development), PostgreSQL-compatible

---

## ⚙️ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/nishalpandit/sanghi.git
cd sanghi
```

### 2. Set up virtual environment
```bash
python -m venv env
# On Windows:
.\env\Scripts\activate
# On macOS/Linux:
source env/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Key variables:
- `OPENAI_API_KEY`: Your OpenAI API key for AI poster generation.
- `OPENAI_IMAGE_MODEL`: e.g. `dall-e-3` or specified model.

### 5. Run Migrations & Start Server
```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000` in your browser.

---

## 📄 License
This project is proprietary and confidential. All rights reserved.
