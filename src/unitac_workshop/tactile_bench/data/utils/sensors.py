import cv2

from unitac_workshop.tactile_bench.data.utils.image_transforms import apply


class BaseSensor:
    def __init__(self, sensor_params={}):
        self.sensor_params = sensor_params

    def read(self, outfile=None):
        raise NotImplementedError

    def process(self, outfile=None):
        img = apply(self.read(), **self.sensor_params)
        if outfile:
            cv2.imwrite(outfile, img)
        return img


class SimSensor(BaseSensor):
    def __init__(self, sensor_params={}, embodiment={}):
        super().__init__(sensor_params)
        self.embodiment = embodiment

    def read(self, outfile=None):
        return self.embodiment.get_tactile_observation()


class RealSensor(BaseSensor):
    def __init__(self, sensor_params={}):
        super().__init__(sensor_params)
        source = sensor_params.get('source', 0)
        exposure = sensor_params.get('exposure', -7)

        self.cam = cv2.VideoCapture(source)

        if not self.cam.isOpened():
            raise RuntimeError(f"Could not open camera source {source}")

        # Only set exposure if explicitly provided
        if "exposure" in sensor_params:
            self.cam.set(cv2.CAP_PROP_EXPOSURE, exposure)

        # Flush initial frames
        for _ in range(5):
            self.cam.read()

    def read(self, outfile=None):
        # Discard a couple of buffered frames
        img = None
        ok = False

        for _ in range(3):
            ok, img = self.cam.read()

        if not ok or img is None:
            raise RuntimeError("Camera frame capture failed")

        return img


class ReplaySensor(BaseSensor):
    def read(self, outfile):
        return cv2.imread(outfile, cv2.IMREAD_UNCHANGED)

    def process(self, outfile):
        return self.read(outfile)


class DummySensor(BaseSensor):
    def read(self, outfile=None):
        return None

    def process(self, outfile=None):
        return None
