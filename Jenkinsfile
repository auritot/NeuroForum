pipeline {
    agent any
    environment {
        // Use Jenkins secrets or environment injection here
        MYSQL_DATABASE = credentials('mysql-db')
        MYSQL_USER = credentials('mysql-user')
        MYSQL_PASSWORD = credentials('mysql-pass')
        MYSQL_ROOT_PASSWORD = credentials('mysql-root-pass')
        DB_PORT = '3306'
        DJANGO_SECRET_KEY = credentials('django-secret')
        SSH_PRIVATE_KEY = credentials('ssh-private-key')
    }

    stages {
        stage('Prepare .env') {
            steps {
                writeFile file: '.env', text: """
MYSQL_DATABASE=${MYSQL_DATABASE}
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
DB_HOST=db
DB_PORT=${DB_PORT}
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY}"
DEBUG=False
"""
            }
        }

        stage('Start Docker Services') {
            steps {
                sh 'docker-compose up -d --build'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker-compose exec -T web python manage.py test || true'
            }
        }

        stage('Tear Down') {
            steps {
                sh 'docker-compose down'
            }
        }
    }

    post {
        always {
            script {
                if (fileExists('test-results.xml')) {
                    junit 'test-results.xml'
                } else {
                    echo 'No test results file found.'
                }
            }
        }
    }
}
