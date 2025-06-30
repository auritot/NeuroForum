pipeline {
    agent any
    options {
        skipDefaultCheckout()
    }

    environment {
        DEBUG = 'False'
    }

    stages {
        stage('Checkout') {
            steps {
                retry(2) {
                    checkout scm
                }
            }
        }

        stage('Prepare & Run') {
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
                        withEnv([
                            "FERNET_KEY=${FERNET_KEY}",
                            "DJANGO_SETTINGS_MODULE=neuroforum_django.settings"
                        ]) {
                            node {
                                // Write env file
                                def envMap = [
                                    'MYSQL_DATABASE': MYSQL_DATABASE,
                                    'MYSQL_USER': MYSQL_USER,
                                    'MYSQL_PASSWORD': MYSQL_PASSWORD,
                                    'MYSQL_ROOT_PASSWORD': MYSQL_ROOT_PASSWORD,
                                    'DB_HOST': 'db',
                                    'DB_PORT': '3306',
                                    'DJANGO_SECRET_KEY': DJANGO_SECRET_KEY,
                                    'SSH_PRIVATE_KEY': SSH_PRIVATE_KEY,
                                    'FERNET_KEY': FERNET_KEY,
                                    'DEBUG': DEBUG
                                ]
                                def envContent = envMap.collect { k, v -> "${k}=${v}" }.join("\n")
                                writeFile file: '.env', text: envContent

                                // Prevent port conflict with override
                                writeFile file: 'docker-compose.override.yml', text: '''
services:
  db:
    ports: []

  redis:
    ports: []
'''
                            }

                            sh '''
                                docker-compose up -d web
                                sleep 5

                                docker exec \
                                    -e FERNET_KEY=$FERNET_KEY \
                                    -e DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE \
                                    neuroforum_django_web_1 \
                                    sh -c "mkdir -p /tmp/test-reports && python -m xmlrunner discover -s . -o /tmp/test-reports"
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            node {
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

                    // Cleanup override
                    sh 'rm -f docker-compose.override.yml'
                }

                echo "Final build result: ${currentBuild.result}"
            }
        }
    }
}
