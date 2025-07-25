cloudops.dockerImage {

    container {
        name 'podman'
        image 'quay.io/podman/stable:latest'
        requests {
            cpu '1'
            memory '4Gi'
        }
        root true
        privileged true
    }

    build { context ->
        def arches = ['amd64', 'arm64']
        arches.each { arch ->
            container('podman') {
                sh "podman build --platform=linux/$arch --tag=$arch ."
                sh "podman image save --format docker-archive localhost/$arch --output image.$arch"
            }
            sh "crossplane xpkg build --package-root=package --embed-runtime-image-tarball=image.$arch --package-file=xpkg.$arch"
        }
        sh "crossplane xpkg push --package-files=${arches.collect{"xpkg.$it"}.join(',')} $context.INTERIM_IMAGE"
    }
}
