pipeline {
    agent any

    environment {
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
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY}"
DEBUG=${DEBUG}
"""
                }
            }
        }

        // Removed "Start Docker Services" to avoid conflicting containers

        stage('Run Tests') {
            steps {
                sh 'docker exec neuroforum_django_web_1 python manage.py test --testrunner xmlrunner.extra.djangotestrunner.XMLTestRunner --output-file=/app/reports/test-results.xml || true'
            }
        }

        // Optional: remove if you don’t want to stop running containers
        // stage('Tear Down') {
        //     steps {
        //         sh 'docker-compose down'
        //     }
        // }
    }

    post {
        always {
            script {
                if (fileExists('reports/test-results.xml')) {
                    junit 'reports/test-results.xml'
                } else {
                    echo 'No test results file found.'
                }
            }
        }
    }
}
