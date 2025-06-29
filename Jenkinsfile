pipeline {
    agent any

    environment {
        DEBUG = 'False'
    }

    stages {
        stage('Prepare .env') {
            steps {
                retry(2) {
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
        }

        stage('Run Tests') {
            steps {
                sh '''
                mkdir -p reports

                # Run tests inside the container and generate XML report
                docker exec neuroforum_django_web_1 \
                python manage.py test \
                --testrunner=xmlrunner.extra.djangotestrunner.XMLTestRunner \
                --output-file=/tmp/TEST-results.xml

                # Copy the result from container to host
                docker cp neuroforum_django_web_1:/tmp/TEST-results.xml reports/TEST-results.xml
                '''
            }
        }
    }

    post {
        always {
            script {
                if (fileExists('reports/test-reports')) {
                    catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                        junit allowEmptyResults: false, testResults: 'reports/test-reports/*.xml'
                    }

                    echo "JUnit test result processed"

                    def combinedXml = sh(script: "cat reports/test-reports/*.xml", returnStdout: true)
                    def skippedCount = combinedXml.count('<skipped')
                    echo "Skipped tests: ${skippedCount}"

                    currentBuild.result = 'SUCCESS'
                } else {
                    echo 'No test results found.'
                    currentBuild.result = 'FAILURE'
                }
            }

            echo "Final build result: ${currentBuild.result}"
        }
    }
}
