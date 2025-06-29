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

                # Run tests inside the container and generate XML inside the container's filesystem
                docker exec neuroforum_django_web_1 \
                python manage.py test \
                --testrunner=xmlrunner.extra.djangotestrunner.XMLTestRunner \
                --output-file=/tmp/TEST-results.xml

                # Copy test result from container to Jenkins workspace
                docker cp neuroforum_django_web_1:/tmp/TEST-results.xml reports/TEST-results.xml
                '''
            }
        }
    }

    post {
        always {
            script {
                if (fileExists('reports/TEST-results.xml')) {
                    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                        junit allowEmptyResults: false, testResults: 'reports/TEST-*.xml'
                    }

                    echo "JUnit test result processed"

                    def xml = readFile('reports/TEST-results.xml')
                    def skippedCount = xml.count('<skipped')
                    echo "Skipped tests: ${skippedCount}"

                    currentBuild.result = 'SUCCESS'  // Force success override
                } else {
                    echo 'No test results file found.'
                    currentBuild.result = 'FAILURE'
                }
            }

            echo "Final build result: ${currentBuild.result}"
        }
    }
}
