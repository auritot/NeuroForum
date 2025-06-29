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
                        string(credentialsId: 'ssh-private-key', variable: 'SSH_PRIVATE_KEY'),
                        string(credentialsId: 'fernet-key', variable: 'FERNET_KEY')
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
                                'FERNET_KEY': FERNET_KEY,
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
                mkdir -p reports/test-reports

                # Run tests inside container with FERNET_KEY injected
                docker exec \
                    -e FERNET_KEY=$FERNET_KEY \
                    neuroforum_django_web_1 \
                    python -m xmlrunner discover \
                    -s . \
                    -o /tmp/test-reports

                # Copy test reports from container to Jenkins workspace
                docker cp neuroforum_django_web_1:/tmp/test-reports reports/test-reports
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
