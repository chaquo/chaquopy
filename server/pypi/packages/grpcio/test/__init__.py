import unittest


# Adapted from https://github.com/grpc/grpc/blob/master/examples/python/helloworld.
class TestGrpcio(unittest.TestCase):

    def setUp(self):
        from concurrent import futures
        import grpc
        from . import helloworld_pb2, helloworld_pb2_grpc

        class Greeter(helloworld_pb2_grpc.GreeterServicer):
            def SayHello(self, request, context):
                return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name)

        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), self.server)
        self.port = self.server.add_insecure_port('localhost:0')
        self.assertTrue(self.port)
        self.server.start()

    def test_greeter(self):
        import grpc
        from . import helloworld_pb2, helloworld_pb2_grpc

        channel = grpc.insecure_channel('localhost:{}'.format(self.port))
        stub = helloworld_pb2_grpc.GreeterStub(channel)
        response = stub.SayHello(helloworld_pb2.HelloRequest(name='world'))
        self.assertEqual("Hello, world!", response.message)

    def tearDown(self):
        self.server.stop(0)
