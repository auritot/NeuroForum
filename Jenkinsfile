pipeline {
    agent any

    environment {
        DJANGO_SETTINGS_MODULE = 'neuroforum_django.settings'
        COMPOSE_FILE = 'docker-compose.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/auritot/NeuroForum.git'
            }
        }

        stage('Start Docker Services') {
            steps {
                sh 'docker-compose up -d --build'
                sh 'sleep 10'  // give time for db/redis/migrations
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker-compose exec web pytest --junitxml=test-results.xml || true'
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
