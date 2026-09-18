from risk_service import RiskService

def test_risk_service():
    risk_service = RiskService()

    account_id = "anson"
    symbol = ['apple', 'tsla']

    # 1 test ok can apply
    valid, reason = risk_service.check_order(
        account_id, symbol[0], "BUY", 100, 200
    )
    assert valid == True 
    risk_service.apply_fill(account_id, symbol[0],"BUY",100)
    assert risk_service.get_position(account_id, symbol[0]) == 100
    print("test 1 ok can apply")

    #2 invalid price
    valid, reason = risk_service.check_order(
        account_id, symbol[0], "BUY", 100, 0
    )
    assert valid == False 
    assert reason == "invalid price"
    print(reason)
    #3 invalid quantity
    valid, reason = risk_service.check_order(
        account_id, symbol[0], "BUY", -1, 100
    )
    assert valid == False
    print(reason)

    #4 exceed max order
    valid, reason = risk_service.check_order(
        account_id, symbol[1], "BUY", 5000, 100
    )
    assert valid == False 
    print("too much buy")
    valid, reason = risk_service.check_order(
        account_id, symbol[0], "SELL", 6000, 10
    )
    assert valid == False
    print("too much sell , ", reason)
    #5 add another symbol
    valid, reason = risk_service.check_order(
        account_id, symbol[1], "SELL", 100,10
    )
    assert valid == True
    risk_service.apply_fill(account_id, symbol[1], "SELL", 100)
    print(reason)
    assert risk_service.get_position(account_id, symbol[1]) == -100
    #6 add another account
    valid, reason = risk_service.check_order(
        "another guy", symbol[0], "BUY", 100, 10
    )
    assert valid == True
    print("add another guy")

def main():
    test_risk_service()
    print("finish all tests")

if __name__ == "__main__":
    main()