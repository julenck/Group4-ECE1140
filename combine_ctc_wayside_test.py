


import track_controller.New_SW_Code.sw_wayside_controller_ui as wayside_sw



def main():
    

    vital1 = wayside_sw.sw_vital_check.sw_vital_check()
    controller1 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital1,"track_controller\\New_SW_Code\\Green_Line_PLC_XandLup.py")
    ui1 = wayside_sw.sw_wayside_controller_ui(controller1)

    ui1.title("Green Line Wayside Controller - X and L Up")
    ui1.geometry("1200x800")


    vital2 = wayside_sw.sw_vital_check.sw_vital_check()
    controller2 = wayside_sw.sw_wayside_controller.sw_wayside_controller(vital2,"track_controller\\New_SW_Code\\Green_Line_PLC_XandLdown.py")


    wayside_sw.tk.mainloop()

if __name__ == "__main__":
    main()
