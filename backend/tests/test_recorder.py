from app.domain.services.recorder import Recorder, RecordingParams


class TestRecordingParams:
    def test_defaults(self):
        params = RecordingParams()
        assert params.resolution == '1920x1080'
        assert params.segment_seconds == 1800
        assert params.bitrate is None
        assert params.fps is None

    def test_bitrate_or_default_explicit(self):
        params = RecordingParams(bitrate=4096)
        assert params.bitrate_or_default() == 4096

    def test_bitrate_or_default_auto_1080p(self):
        params = RecordingParams(resolution='1920x1080')
        assert params.bitrate_or_default() == 2048

    def test_bitrate_or_default_auto_720p(self):
        params = RecordingParams(resolution='1280x720')
        assert params.bitrate_or_default() == 1024

    def test_bitrate_or_default_auto_480p(self):
        params = RecordingParams(resolution='640x480')
        assert params.bitrate_or_default() == 512

    def test_fps_or_default_explicit(self):
        params = RecordingParams(fps=30)
        assert params.fps_or_default() == 30

    def test_fps_or_default_null(self):
        params = RecordingParams()
        assert params.fps_or_default() == 25


class TestBuildFFmpegCmd:
    def test_default_params(self, tmp_path):
        params = RecordingParams()
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert cmd[0] == 'ffmpeg'
        assert '-c:v' in cmd
        assert 'libx264' in cmd
        assert '-b:v' in cmd
        assert '2048k' in cmd  # 1920x1080 -> 2048
        assert '-r' in cmd
        assert '25' in cmd
        assert '-s' in cmd
        assert '1920x1080' in cmd
        assert str(output_path) in cmd

    def test_custom_bitrate(self, tmp_path):
        params = RecordingParams(bitrate=4096)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '4096k' in cmd

    def test_custom_fps(self, tmp_path):
        params = RecordingParams(fps=30)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-r' in cmd
        assert '30' in cmd

    def test_custom_resolution(self, tmp_path):
        params = RecordingParams(resolution='1280x720')
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-s' in cmd
        assert '1280x720' in cmd

    def test_custom_segment_seconds(self, tmp_path):
        params = RecordingParams(segment_seconds=600)
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '-t' in cmd
        assert '600' in cmd

    def test_preset_like_params(self, tmp_path):
        """Simulate a preset with 720p@1024kbps@20fps"""
        params = RecordingParams(
            resolution='1280x720',
            segment_seconds=600,
            bitrate=1024,
            fps=20,
        )
        recorder = Recorder(temp_dir=str(tmp_path))
        rtsp_url = 'rtsp://192.168.1.100:554/stream'
        output_path = tmp_path / 'output.mp4'
        cmd = recorder._build_ffmpeg_cmd(rtsp_url, output_path, params)
        assert '1280x720' in cmd
        assert '1024k' in cmd
        assert '20' in cmd
        assert '600' in cmd
