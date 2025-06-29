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
                    script {
                        def envContent = 
                            "MYSQL_DATABASE=${MYSQL_DATABASE}\n" +
                            "MYSQL_USER=${MYSQL_USER}\n" +
                            "MYSQL_PASSWORD=${MYSQL_PASSWORD}\n" +
                            "MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}\n" +
                            "DB_HOST=db\n" +
                            "DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}\n" +
                            "SSH_PRIVATE_KEY=\"${SSH_PRIVATE_KEY}\"\n" +
                            "DEBUG=${DEBUG}\n"

                        writeFile file: '.env', text: envContent
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                docker exec neuroforum_django_web_1 \
                python manage.py test \
                --testrunner=xmlrunner.extra.djangotestrunner.XMLTestRunner \
                -- output_dir=/app/reports || true
                '''
            }
        }
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
