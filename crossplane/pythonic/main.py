"""The composition function's main CLI."""

import warnings
warnings.filterwarnings('ignore', module='^google[.]protobuf[.]runtime_version$', lineno=98)

import argparse
import os
import shlex
import sys
import pip._internal.cli.main
from crossplane.function import logging, runtime

from . import function


def main():
    parser = argparse.ArgumentParser('Forta Crossplane Function')
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Emit debug logs.',
    )
    parser.add_argument(
        '--address',
        default='0.0.0.0:9443',
        help='Address at which to listen for gRPC connections, default: 0.0.0.0:9443',
    )
    parser.add_argument(
        '--tls-certs-dir',
        help='Serve using mTLS certificates.',
    )
    parser.add_argument(
        '--insecure',
        action='store_true',
        help='Run without mTLS credentials. If you supply this flag --tls-certs-dir will be ignored.',
    )
    parser.add_argument(
        '--pip-install',
        help='Pip install command to install additional Python packages.'
    )
    parser.add_argument(
        '--python-path',
        action='append',
        help='Filing system directories to add to the python path',
    )
    parser.add_argument(
        '--allow-oversize-protos',
        action='store_true',
        help='Allow oversized protobuf messages'
    )
    args = parser.parse_args()
    if not args.tls_certs_dir:
        args.tls_certs_dir = os.getenv('TLS_SERVER_CERTS_DIR')

    if args.pip_install:
        pip._internal.cli.main.main(['install', *shlex.split(args.pip_install)])

    if args.python_path:
        for path in reversed(args.python_path):
            sys.path.insert(0, path)

    if args.allow_oversize_protos:
        from google.protobuf.internal import api_implementation
        if api_implementation._c_module:
            api_implementation._c_module.SetAllowOversizeProtos(True)

    logging.configure(logging.Level.DEBUG if args.debug else logging.Level.INFO)
    runtime.serve(
        function.FunctionRunner(),
        args.address,
        creds=runtime.load_credentials(args.tls_certs_dir),
        insecure=args.insecure,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Exception running main: {e}", file=sys.stderr)
        sys.exit(1)
