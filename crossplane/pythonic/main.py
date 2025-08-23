"""The composition function's main CLI."""

import argparse
import asyncio
import logging
import os
import pathlib
import shlex
import signal
import sys
import traceback

import crossplane.function.logging
import crossplane.function.proto.v1.run_function_pb2_grpc as grpcv1
import grpc
import pip._internal.cli.main

from . import function


def main():
    asyncio.run(Main().main())


class Main:
    async def main(self):
        parser = argparse.ArgumentParser('Forta Crossplane Function')
        parser.add_argument(
            '--debug', '-d',
            action='store_true',
            help='Emit debug logs.',
        )
        parser.add_argument(
            '--log-name-width',
            type=int,
            default=40,
            metavar='WIDTH',
            help='Width of the logger name in the log output, default 40',
        )
        parser.add_argument(
            '--address',
            default='0.0.0.0:9443',
            help='Address at which to listen for gRPC connections, default: 0.0.0.0:9443',
        )
        parser.add_argument(
            '--tls-certs-dir',
            default=os.getenv('TLS_SERVER_CERTS_DIR'),
            metavar='DIRECTORY',
            help='Serve using mTLS certificates.',
        )
        parser.add_argument(
            '--insecure',
            action='store_true',
            help='Run without mTLS credentials. If you supply this flag --tls-certs-dir will be ignored.',
        )
        parser.add_argument(
            '--packages',
            action='store_true',
            help='Discover python packages from function-pythonic ConfigMaps.'
        )
        parser.add_argument(
            '--packages-secrets',
            action='store_true',
            help='Also Discover python packages from function-pythonic Secrets.'
        )
        parser.add_argument(
            '--packages-namespace',
            action='append',
            default=[],
            metavar='NAMESPACE',
            help='Namespaces to discover function-pythonic ConfigMaps in, default is cluster wide.',
        )
        parser.add_argument(
            '--packages-dir',
            default='./pythonic-packages',
            metavar='DIRECTORY',
            help='Directory to store discovered function-pythonic ConfigMaps to, defaults "<cwd>/pythonic-packages"'
        )
        parser.add_argument(
            '--pip-install',
            metavar='COMMAND',
            help='Pip install command to install additional Python packages.'
        )
        parser.add_argument(
            '--python-path',
            action='append',
            default=[],
            metavar='DIRECTORY',
            help='Filing system directories to add to the python path',
        )
        parser.add_argument(
            '--allow-oversize-protos',
            action='store_true',
            help='Allow oversized protobuf messages'
        )
        args = parser.parse_args()
        self.configure_logging(args)

        if args.pip_install:
            pip._internal.cli.main.main(['install', *shlex.split(args.pip_install)])

        # enables read only volumes or mismatched uid volumes
        sys.dont_write_bytecode = True
        for path in reversed(args.python_path):
            sys.path.insert(0, str(pathlib.Path(path).resolve()))

        if args.allow_oversize_protos:
            from google.protobuf.internal import api_implementation
            if api_implementation._c_module:
                api_implementation._c_module.SetAllowOversizeProtos(True)

        grpc.aio.init_grpc_aio()
        grpc_runner = function.FunctionRunner(args.debug)
        grpc_server = grpc.aio.server()
        grpcv1.add_FunctionRunnerServiceServicer_to_server(grpc_runner, grpc_server)
        if args.tls_certs_dir:
            certs = pathlib.Path(args.tls_certs_dir)
            grpc_server.add_secure_port(
                args.address,
                grpc.ssl_server_credentials(
                    private_key_certificate_chain_pairs=[(
                        (certs / 'tls.key').read_bytes(),
                        (certs / 'tls.crt').read_bytes(),
                    )],
                    root_certificates=(certs / 'ca.crt').read_bytes(),
                    require_client_auth=True,
                ),
            )
        else:
            if not args.insecure:
                raise ValueError('Either --tls-certs-dir or --insecure must be specified')
            grpc_server.add_insecure_port(args.address)
        await grpc_server.start()

        if args.packages:
            from . import packages
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(grpc_server.wait_for_termination())
                tasks.create_task(packages.operator(
                    grpc_server,
                    grpc_runner,
                    args.packages_secrets,
                    args.packages_namespace,
                    args.packages_dir,
                ))
        else:
            def stop():
                asyncio.ensure_future(grpc_server.stop(5))
            loop = asyncio.get_event_loop()
            loop.add_signal_handler(signal.SIGINT, stop)
            loop.add_signal_handler(signal.SIGTERM, stop)
            await grpc_server.wait_for_termination()

    def configure_logging(self, args):
        formatter = Formatter(args.log_name_width)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if args.debug else logging.INFO)


class Formatter(logging.Formatter):
    def __init__(self, name_width):
        super(Formatter, self).__init__(
            f"[{{asctime}}.{{msecs:03.0f}}] {{sname:{name_width}.{name_width}}} [{{levelname:8.8}}] {{message}}",
            '%Y-%m-%d %H:%M:%S',
            '{',
        )
        self.name_width = name_width

    def format(self, record):
        record.sname = record.name
        extra = len(record.sname) - self.name_width
        if extra > 0:
            names = record.sname.split('.')
            for ix, name in enumerate(names):
                if len(name) > extra:
                    names[ix] = name[extra:]
                    break
                names[ix] = name[:1]
                extra -= len(name) - 1
            record.sname = '.'.join(names)
        return super(Formatter, self).format(record)


if __name__ == '__main__':
    main()
