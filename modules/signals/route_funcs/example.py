# Program always calls "main" function to run the code.
def main():
    print("This is an example route function.")

    # Whatever this returns can be put into the response body by using the placeholder "func_response" in the HTML response. 
    # Returns 200 as the http code. Remove the second item (The 200) to use the default http code set in the route.
    return "Hello from the example route function!", 200

# Program calls "view" function to get data to show on the route.
def view():
    """
    This function is called to get whatever data is assosciated with the function that this route gathered.
    Eg, a route was called and set "your_key" to "your_value", then this function COULD return "your_value".

    So, "main" gathers data -> "view" returns data.
    
    Eg, for usage tracking,
    main() increments a counter each time the route is called,
    view() returns the current value of that counter.
    """ 
    return "This is the view function response.", 200