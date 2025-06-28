pipeline {
    agent any

    environment {
        DJANGO_SETTINGS_MODULE = 'neuroforum_django.settings'
        COMPOSE_FILE = 'docker-compose.yml'
    }

    stages {
        stage('Start Docker Services') {
            steps {
                sh 'docker-compose up -d --build'
                sh 'sleep 10'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker-compose exec web pytest --ds=neuroforum_django.settings --junitxml=test-results.xml || true'
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
            junit 'test-results.xml'
        }
    }
}
