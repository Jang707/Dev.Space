def init_card_v2(self):
        #oth check if it eventually works like a v1 card
        for i in range(_CMD_TIMEOUT):
            self.cmd(55, 0, 0)
            if self.cmd(41, 0, 0) == 0:
                self.cdv = 512
                print("[SDCard] v1a card")
                return
            time.sleep_ms(50)

        # current state is undefined, so try again from beginning

        # clock card at least 100 cycles with cs high
        for i in range(16):
            self.spi.write(b"\xff")

        # CMD0: init card; should return _R1_IDLE_STATE (allow 5 attempts)
        for _ in range(5):
            if self.cmd(0, 0, 0x95) == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card")

        # CMD8: determine card version, but ignore in this case
        r = self.cmd(8, 0x01AA, 0x87, 4)
        #oth

        for i in range(_CMD_TIMEOUT):
            self.cmd(58, 0, 0, 4)
            self.cmd(55, 0, 0)
            if self.cmd(41, 0x40000000, 0) == 0:
                self.cmd(58, 0, 0, 4)
                self.cdv = 1
                print("[SDCard] v2 card")
                return
            time.sleep_ms(50) #oth
        raise OSError("timeout waiting for v2 card")