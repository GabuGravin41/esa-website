# ESA-KU

Engineering Students Association - Kenyatta University (ESA-KU) platform.

## Deployment to Render

To deploy this project to Render:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the following settings:
   - **Name**: Choose a name for your service
   - **Environment**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn puddle.wsgi:application`
   - **Root Directory**: puddle/

4. Add the required environment variables:
   - `SECRET_KEY`: Your Django secret key
   - `DJANGO_DEBUG`: Set to False for production
   - `ALLOWED_HOSTS`: Your Render domain, e.g. example.onrender.com
   - `DATABASE_URL`: This will be automatically added if you create a PostgreSQL database on Render
   - `EMAIL_HOST_USER`: Your email for sending emails
   - `EMAIL_HOST_PASSWORD`: Your email password or app password
   - `MPESA_CONSUMER_KEY`: Your M-Pesa API consumer key
   - `MPESA_CONSUMER_SECRET`: Your M-Pesa API consumer secret
   - `MPESA_SHORTCODE`: Your M-Pesa shortcode
   - `MPESA_PASSKEY`: Your M-Pesa passkey
   - `MPESA_CALLBACK_URL`: Your M-Pesa callback URL
   - `PAYPAL_CLIENT_ID`: Your PayPal client ID
   - `PAYPAL_SECRET`: Your PayPal secret
   - `PAYPAL_MODE`: sandbox or live

5. Create a PostgreSQL database on Render and link it to your web service

## Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: 
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file in the project root with the required environment variables
6. Run migrations: `python manage.py migrate`
7. Start the development server: `python manage.py runserver`
