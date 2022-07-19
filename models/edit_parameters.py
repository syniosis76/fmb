class edit_parameters():
  position = 0.0, 0.0
  rotation = 0.0
  zoom = 1.0
  ratio = None
  brightness = 0.0
  contrast = 0.0
  saturation = 0.0
  gamma = 0.0

  def assign_adjustment(self, parameters):
    self.brightness = parameters.brightness
    self.contrast = parameters.contrast
    self.saturation = parameters.saturation
    self.gamma = parameters.gamma

  def reset_adjustment(self):
    self.brightness = 0.0
    self.contrast = 0.0
    self.saturation = 0.0
    self.gamma = 0.0

  def reset_position(self):
    self.position = 0.0, 0.0
    self.rotation = 0.0
    self.zoom = 1.0
    self.ratio = None  