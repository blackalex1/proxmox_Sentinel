import pytest

def test_parse_remote_iptables_line():
    from modules.proxmox.monitor.remote.traffic import parse_remote_iptables_line
    
    # 1. Проверяем правильный разбор исходящего соединения на sensitive порт
    log_line = (
        "May 25 02:29:00 vps kernel: [123.456] REMOTE_CONN_OUT: "
        "IN= OUT=eth0 SRC=198.51.100.50 DST=203.0.113.100 LEN=60 "
        "TOS=0x00 PREC=0x00 TTL=64 ID=21151 DF PROTO=TCP SPT=43210 DPT=22"
    )
    
    event = parse_remote_iptables_line(log_line)
    assert event is not None
    assert event['direction'] == 'OUT'
    assert event['proto'] == 'TCP'
    assert event['src'] == '198.51.100.50'
    assert event['dst'] == '203.0.113.100'
    assert event['spt'] == 43210
    assert event['dpt'] == 22

    # 2. Игнорируем нерелевантные строки логов
    invalid_line = "May 25 02:29:00 vps sshd[12345]: Accepted password for root from 1.1.1.1"
    assert parse_remote_iptables_line(invalid_line) is None
