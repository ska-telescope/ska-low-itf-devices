from .conftest import expect_attribute


def test_switching(proxr_device, number_of_relays):
    """
    Switch all relays on the device

    :param proxr_device: Device proxy for the ProXR relay under test.
    :param number_of_relays: the number of relays on the board.
    """

    # Sequentially switch all the relays on and off.
    for i in range(1, number_of_relays + 1):
        setattr(proxr_device, f"Relay{i}", True)
        expect_attribute(proxr_device, f"Relay{i}", True)
        setattr(proxr_device, f"Relay{i}", False)
        expect_attribute(proxr_device, f"Relay{i}", False)
