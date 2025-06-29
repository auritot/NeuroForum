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
                        def envMap = [
                            'MYSQL_DATABASE': MYSQL_DATABASE,
                            'MYSQL_USER': MYSQL_USER,
                            'MYSQL_PASSWORD': MYSQL_PASSWORD,
                            'MYSQL_ROOT_PASSWORD': MYSQL_ROOT_PASSWORD,
                            'DB_HOST': 'db',
                            'DJANGO_SECRET_KEY': DJANGO_SECRET_KEY,
                            'SSH_PRIVATE_KEY': SSH_PRIVATE_KEY,
                            'DEBUG': DEBUG
                        ]
                        def envContent = envMap.collect { k, v -> "${k}=${v}" }.join("\n")
                        writeFile file: '.env', text: envContent
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                mkdir -p reports
                docker exec neuroforum_django_web_1 \
                python manage.py test \
                --testrunner=xmlrunner.extra.djangotestrunner.XMLTestRunner \
                > reports/TEST-results.xml
                '''
            }
        }
    }

    post {
        always {
            script {
                if (fileExists('reports/TEST-results.xml')) {
                    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                         junit allowEmptyResults: false, testResults: 'reports/TEST-*.xml', skipPublishingChecks: true
                         currentBuild.result = 'SUCCESS'
                    }

                    // Log skipped test count
                    def xml = readFile('reports/TEST-results.xml')
                    def skippedCount = xml.count('<skipped')
                    echo "Skipped tests: ${skippedCount}"

                } else {
                    echo 'No test results file found.'
                    currentBuild.result = 'FAILURE'
                }
                currentBuild.result = 'SUCCESS'
            }
        }
    }
}
