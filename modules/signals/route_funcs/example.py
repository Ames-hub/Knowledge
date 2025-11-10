# Program always calls "main" function to run the code.
def main():
    print("This is an example route function.")

    # Whatever this returns can be put into the response body by using the placeholder "func_response" in the HTML response. 
    # Returns 200 as the http code. Remove the second item (The 200) to use the default http code set in the route.
    return "Hello from the example route function!", 200