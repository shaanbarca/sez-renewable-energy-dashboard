class BasicModel:
    """
    A basic model that applies a parameter to an input value.

    Attributes:
        parameter (float): The parameter used in the model calculations.
    """

    def __init__(self, parameter: float):
        """
        Initializes the BasicModel with a given parameter.

        Args:
            parameter (float): The parameter to be used in the model.
        """
        self.parameter = parameter

    def run(self, input_value: float):
        """
        Applies the model's parameter to the input value.

        Args:
            input_value (float): The input value to be processed.

        Returns:
            float: The result of multiplying the input value by the parameter.
        """
        return input_value * self.parameter
