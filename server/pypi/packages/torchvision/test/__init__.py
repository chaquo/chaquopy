import unittest


class TestTorchvision(unittest.TestCase):

    # Based on https://pytorch.org/hub/pytorch_vision_mobilenet_v2/
    def test_model(self):
        import json
        import os
        import PIL
        import torch
        from torchvision import models, transforms

        SIZE = 224
        preprocess = transforms.Compose([
            transforms.Resize(SIZE),
            transforms.CenterCrop(SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])])

        cache_url(models.mobilenetv2.model_urls["mobilenet_v2"],
                  f"{torch.hub._get_torch_home()}/hub/checkpoints")
        model = models.mobilenet_v2(pretrained=True)
        model.eval()

        TEST_DIR = os.path.dirname(__file__)
        with open(f"{TEST_DIR}/imagenet1000_clsidx_to_labels.json") as clsidx_file:
            classes = {int(index): names.split(",")[0]
                       for index, names in json.load(clsidx_file).items()}

        count = 0
        for filename in os.listdir(TEST_DIR):
            if filename.endswith(".jpg"):
                count += 1
                with self.subTest(filename=filename):
                    input = preprocess(PIL.Image.open(f"{TEST_DIR}/{filename}"))
                    with torch.no_grad():
                        output = model(input.unsqueeze(0))
                    self.assertEqual(filename.replace(".jpg", ""),
                                     classes[int(output.argmax())])
        self.assertEqual(4, count)

    # Test one of the C++ operators.
    def test_nms(self):
        import torch
        from torchvision.ops import nms

        boxes = torch.Tensor([
            [1, 1, 4, 4],   # intersection=4, union=30, iou=0.133
            [2, 2, 7, 7],   #

            [8, 1, 9, 2],   # No overlap
        ])

        scores = torch.Tensor([0, 1, 2])
        self.assertEqual([2, 1, 0], nms(boxes, scores, 0.2).tolist())
        self.assertEqual([2, 1], nms(boxes, scores, 0.1).tolist())

        scores = torch.Tensor([2, 1, 0])
        self.assertEqual([0, 1, 2], nms(boxes, scores, 0.2).tolist())
        self.assertEqual([0, 2], nms(boxes, scores, 0.1).tolist())


def cache_url(url, dir_name, base_name=None):
    import os

    if base_name is None:
        base_name = os.path.basename(url)
    filename = f"{dir_name}/{base_name}"
    if not os.path.exists(filename):
        os.makedirs(dir_name, exist_ok=True)
        data = read_url(url)
        with open(filename, "wb") as f:
            f.write(data)


# Downloading a URL with "Connection: close", as urllib does, causes an intermittent
# network problem on the emulator (https://issuetracker.google.com/issues/150758736). For
# small files we could just retry until it succeeds, but for large files a failure is much more
# likely, and we might have to keep retrying for several minutes. So use the stdlib's low-level
# HTTP API to make a request with no Connection header.
def read_url(url):
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import urlparse

    parsed = urlparse(url)
    conn_cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    conn = conn_cls(parsed.hostname, parsed.port)
    full_path = parsed.path
    if parsed.query:
        full_path += "?" + parsed.query
    conn.request("GET", full_path)
    data = conn.getresponse().read()
    conn.close()
    return data
