pipeline {
    agent any

    environment {
        DB_PORT = '3306'
        DEBUG = 'False'
    }

    stages {
        stage('Prepare .env') {
            steps {
                withCredentials([
                    string(credentialsId: 'mysql-db', variable: 'MYSQL_DATABASE'),
                    string(credentialsId: 'mysql-user', variable: 'MYSQL_USER'),
                    string(credentialsId: 'mysql-pass', variable: 'MYSQL_PASSWORD'),
                    string(credentialsId: 'mysql-root-pass', variable: 'MYSQL_ROOT_PASSWORD'),
                    string(credentialsId: 'django-secret', variable: 'DJANGO_SECRET_KEY'),
                    string(credentialsId: 'ssh-private-key', variable: 'SSH_PRIVATE_KEY')
                ]) {
                    writeFile file: '.env', text: """
MYSQL_DATABASE=${MYSQL_DATABASE}
MYSQL_USER=${MYSQL_USER}
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
DB_HOST=db
DB_PORT=${DB_PORT}
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY}"
DEBUG=${DEBUG}
"""
                }
            }
        }

        stage('Start Docker Services') {
            steps {
                sh 'docker-compose up -d --build'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker-compose exec -T web python manage.py test --testrunner xmlrunner.extra.djangotestrunner.XMLTestRunner --output-file=test-results.xml || true'
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
