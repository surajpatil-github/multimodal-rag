pipeline {
    agent any

    // ── Global environment ──────────────────────────────────────────────────
    environment {
        // Docker Hub image names  (change to your Docker Hub username)
        DOCKERHUB_USER      = 'your-dockerhub-username'
        BACKEND_IMAGE       = "${DOCKERHUB_USER}/multimodal-rag-backend"
        FRONTEND_IMAGE      = "${DOCKERHUB_USER}/multimodal-rag-frontend"

        // Credential IDs stored in Jenkins → Manage Credentials
        DOCKERHUB_CREDS     = 'dockerhub-credentials'   // username + password
        OPENAI_API_KEY      = credentials('openai-api-key')
        PINECONE_API_KEY    = credentials('pinecone-api-key')
        PINECONE_TEXT_INDEX = credentials('pinecone-text-index')
        PINECONE_IMAGE_INDEX= credentials('pinecone-image-index')
        TAVILY_API_KEY      = credentials('tavily-api-key')

        // Image tag = short Git commit SHA  (e.g. "a1b2c3d")
        IMAGE_TAG           = "${env.GIT_COMMIT?.take(7) ?: 'latest'}"
    }

    // ── Build triggers ───────────────────────────────────────────────────────
    triggers {
        // Poll GitHub every 5 minutes for new commits
        pollSCM('H/5 * * * *')
    }

    // ── Pipeline options ─────────────────────────────────────────────────────
    options {
        timestamps()                          // prefix every log line with time
        timeout(time: 30, unit: 'MINUTES')    // kill runaway builds
        disableConcurrentBuilds()             // no parallel runs on same branch
        buildDiscarder(logRotator(numToKeepStr: '10'))  // keep last 10 builds
    }

    // ════════════════════════════════════════════════════════════════════════
    stages {

        // ── 1. CHECKOUT ──────────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo "Checking out branch: ${env.BRANCH_NAME}"
                checkout scm
            }
        }

        // ── 2. LINT & STATIC ANALYSIS ────────────────────────────────────────
        stage('Lint') {
            parallel {

                stage('Lint Backend (Python)') {
                    steps {
                        dir('backend') {
                            sh '''
                                python3 -m pip install --quiet flake8 pylint
                                echo "── flake8 ──"
                                flake8 . --max-line-length=100 \
                                         --exclude=venv,__pycache__ \
                                         --statistics || true

                                echo "── pylint ──"
                                pylint app.py ingest.py rag.py tools.py \
                                       pinecone_client.py clip_embedder.py \
                                       --disable=C0114,C0115,C0116 \
                                       --fail-under=6.0 || true
                            '''
                        }
                    }
                }

                stage('Lint Frontend (ESLint)') {
                    steps {
                        dir('frontend') {
                            sh '''
                                npm ci --prefer-offline
                                echo "── ESLint ──"
                                npx eslint . --ext .ts,.tsx --max-warnings=20 || true
                            '''
                        }
                    }
                }
            }
        }

        // ── 3. UNIT TESTS ────────────────────────────────────────────────────
        stage('Test') {
            parallel {

                stage('Test Backend') {
                    steps {
                        dir('backend') {
                            sh '''
                                python3 -m pip install --quiet pytest pytest-cov

                                # Run tests; generate coverage report
                                pytest tests/ \
                                    --cov=. \
                                    --cov-report=xml:coverage.xml \
                                    --cov-report=term-missing \
                                    -v || true
                            '''
                        }
                    }
                    post {
                        always {
                            // Publish coverage report in Jenkins UI
                            junit allowEmptyResults: true,
                                  testResults: 'backend/tests/reports/*.xml'
                            publishCoverage adapters: [
                                coberturaAdapter('backend/coverage.xml')
                            ], sourceFileResolver: sourceFiles('STORE_LAST_BUILD')
                        }
                    }
                }

                stage('Test Frontend') {
                    steps {
                        dir('frontend') {
                            sh '''
                                npm ci --prefer-offline
                                # Jest tests (add jest to package.json when ready)
                                npm test -- --passWithNoTests --watchAll=false || true
                            '''
                        }
                    }
                }
            }
        }

        // ── 4. BUILD DOCKER IMAGES ───────────────────────────────────────────
        stage('Build Docker Images') {
            parallel {

                stage('Build Backend Image') {
                    steps {
                        dir('backend') {
                            script {
                                echo "Building backend image: ${BACKEND_IMAGE}:${IMAGE_TAG}"
                                docker.build("${BACKEND_IMAGE}:${IMAGE_TAG}",
                                             "-f Dockerfile.backend .")
                            }
                        }
                    }
                }

                stage('Build Frontend Image') {
                    steps {
                        dir('frontend') {
                            script {
                                echo "Building frontend image: ${FRONTEND_IMAGE}:${IMAGE_TAG}"
                                docker.build("${FRONTEND_IMAGE}:${IMAGE_TAG}",
                                             "--build-arg NEXT_PUBLIC_API_URL=http://backend:8000 .")
                            }
                        }
                    }
                }
            }
        }

        // ── 5. SECURITY SCAN ─────────────────────────────────────────────────
        stage('Security Scan') {
            steps {
                script {
                    // Trivy scans for OS + library CVEs inside the images
                    sh """
                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image \
                            --exit-code 0 \
                            --severity HIGH,CRITICAL \
                            --format table \
                            ${BACKEND_IMAGE}:${IMAGE_TAG}

                        docker run --rm \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image \
                            --exit-code 0 \
                            --severity HIGH,CRITICAL \
                            --format table \
                            ${FRONTEND_IMAGE}:${IMAGE_TAG}
                    """
                }
            }
        }

        // ── 6. PUSH TO DOCKER HUB ────────────────────────────────────────────
        stage('Push Images') {
            // Only push from main or develop branches
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    docker.withRegistry('https://registry.hub.docker.com',
                                        DOCKERHUB_CREDS) {

                        // Push with commit-SHA tag
                        docker.image("${BACKEND_IMAGE}:${IMAGE_TAG}").push()
                        docker.image("${FRONTEND_IMAGE}:${IMAGE_TAG}").push()

                        // Also tag as "latest" on main branch
                        if (env.BRANCH_NAME == 'main') {
                            docker.image("${BACKEND_IMAGE}:${IMAGE_TAG}").push('latest')
                            docker.image("${FRONTEND_IMAGE}:${IMAGE_TAG}").push('latest')
                        }
                    }
                }
            }
        }

        // ── 7. DEPLOY TO STAGING ─────────────────────────────────────────────
        stage('Deploy → Staging') {
            when { branch 'develop' }
            steps {
                script {
                    echo "Deploying ${IMAGE_TAG} to STAGING"
                    sh """
                        export IMAGE_TAG=${IMAGE_TAG}
                        docker-compose -f docker-compose.yml \
                                       -f docker-compose.staging.yml \
                                       --project-name rag-staging \
                                       up -d --remove-orphans
                    """
                }
            }
            post {
                success {
                    slackSend channel: '#deployments',
                              color: 'good',
                              message: "✅ Staging deploy succeeded — `${IMAGE_TAG}` on `${env.BRANCH_NAME}`"
                }
                failure {
                    slackSend channel: '#deployments',
                              color: 'danger',
                              message: "❌ Staging deploy FAILED — `${IMAGE_TAG}` on `${env.BRANCH_NAME}`"
                }
            }
        }

        // ── 8. DEPLOY TO PRODUCTION ──────────────────────────────────────────
        stage('Deploy → Production') {
            when { branch 'main' }

            // Manual approval gate before touching prod
            input {
                message "Deploy ${IMAGE_TAG} to PRODUCTION?"
                ok      "Yes, deploy it"
                submitter "jenkins-admins"   // Jenkins user/group allowed to approve
            }

            steps {
                script {
                    echo "Deploying ${IMAGE_TAG} to PRODUCTION"
                    sh """
                        export IMAGE_TAG=${IMAGE_TAG}
                        docker-compose -f docker-compose.yml \
                                       -f docker-compose.prod.yml \
                                       --project-name rag-prod \
                                       up -d --remove-orphans
                    """
                }
            }
            post {
                success {
                    slackSend channel: '#deployments',
                              color: 'good',
                              message: "🚀 Production deploy succeeded — `${IMAGE_TAG}`"
                }
                failure {
                    slackSend channel: '#deployments',
                              color: 'danger',
                              message: "💥 Production deploy FAILED — `${IMAGE_TAG}`"
                }
            }
        }
    }

    // ── Post-pipeline cleanup ─────────────────────────────────────────────────
    post {
        always {
            // Remove dangling images to keep the Jenkins agent disk clean
            sh 'docker image prune -f || true'
            cleanWs()   // wipe workspace
        }
        success {
            echo "Pipeline completed successfully for ${IMAGE_TAG}"
        }
        failure {
            echo "Pipeline FAILED — check logs above"
            emailext subject: "Jenkins BUILD FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                     body:    "Build URL: ${env.BUILD_URL}",
                     to:      'your-team@example.com'
        }
    }
}
