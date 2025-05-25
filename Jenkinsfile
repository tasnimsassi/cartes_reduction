pipeline {
    agent any

    environment {
        MODULE_NAME = "cartes_reduction"
        GIT_CREDENTIALS = 'github-pat'
        EXTRA_ADDONS_HOST_PATH = "/home/tasnim/odoo17/addons"
    }

    stages {


        stage('Deploy module') {
            steps {
                echo "Copie du module dans le dossier extra-addons local..."
                sh """
                    rm -rf ${EXTRA_ADDONS_HOST_PATH}/${MODULE_NAME}
                    cp -r . ${EXTRA_ADDONS_HOST_PATH}/${MODULE_NAME}
                """
            }
        }

        stage('Restart Odoo container') {
            steps {
                echo "Redémarrage du conteneur Odoo..."
                sh "docker restart odoo_docker_odoo_1"
            }
        }
    }
}
