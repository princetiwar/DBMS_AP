from django.shortcuts import render,redirect
from ecommerceapp.models import Contact,Product,OrderUpdate,Orders
from django.contrib import messages
from math import ceil
from ecommerceapp import keys
from django.conf import settings
MERCHANT_KEY=keys.MK
import json
from django.views.decorators.csrf import csrf_exempt
from PayTm import Checksum

# Create your views here.
def index(request):

    allProds = []
    catprods = Product.objects.values('category','id')
    print(catprods)
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prod= Product.objects.filter(category=cat)
        n=len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        allProds.append([prod, range(1, nSlides), nSlides])

    params= {'allProds':allProds}

    return render(request,"index.html",params)

    
def contact(request):
    if request.method=="POST":
        name=request.POST.get("name")
        email=request.POST.get("email")
        desc=request.POST.get("desc")
        pnumber=request.POST.get("pnumber")
        myquery=Contact(name=name,email=email,desc=desc,phonenumber=pnumber)
        myquery.save()
        messages.info(request,"we will get back to you soon..")
        return render(request,"contact.html")


    return render(request,"contact.html")

def about(request):
    return render(request,"about.html")



def checkout(request):
    if not request.user.is_authenticated:
        messages.warning(request,"Login & Try Again")
        return redirect('/auth/login')

    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amt')
        email = request.POST.get('email', '')
        address1 = request.POST.get('address1', '')
        address2 = request.POST.get('address2','')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        Order = Orders(items_json=items_json,name=name,amount=amount, email=email, address1=address1,address2=address2,city=city,state=state,zip_code=zip_code,phone=phone)
        print(amount)
        Order.save()
        update = OrderUpdate(order_id=Order.order_id,update_desc="the order has been placed")
        update.save()
        thank = True
# # PAYMENT INTEGRATION

        id = Order.order_id
        oid=str(id)+"ShopyCart"
        param_dict = {

            'MID':keys.MID,
            'ORDER_ID': oid,
            'TXN_AMOUNT': str(amount),
            'CUST_ID': email,
            'INDUSTRY_TYPE_ID': 'Retail',
            'WEBSITE': 'WEBSTAGING',
            'CHANNEL_ID': 'WEB',
            'CALLBACK_URL': 'http://127.0.0.1:8000/handlerequest/',

        }
        param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
        return render(request, 'paytm.html', {'param_dict': param_dict})

    return render(request, 'checkout.html')

@csrf_exempt
def handlerequest(request):
    form = request.POST
    response_dict = {}
    
    if form is not None:
        for i in form.keys():
            response_dict[i] = form[i]
            if i == 'CHECKSUMHASH':
                checksum = form[i]

    try:
        cust_id = response_dict.get('CUSTID')  # Use get method to avoid KeyError
    except KeyError:
        cust_id = None
    
    param_dict = {
        'MID': keys.MID,
        'ORDER_ID': response_dict.get('ORDERID', ''),  # Use get method with a default value
        'TXN_AMOUNT': response_dict.get('TXNAMOUNT', ''),  # Use get method with a default value
        'CUST_ID': cust_id,
        'CHECKSUMHASH': response_dict.get('CHECKSUMHASH', '')  # Use get method with a default value
    }

    param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)

    return render(request, 'paytm.html', {'param_dict': param_dict})


    # Calculate or retrieve the checksum value here
    param_dict.pop('CHECKSUMHASH', None)  # Remove the existing CHECKSUMHASH to recalculate it
    checksum = Checksum.generate_checksum(param_dict, MERCHANT_KEY)

    # Now you can use the `checksum` variable in the `verify` line
    verify = Checksum.verify_checksum(response_dict, keys.MK, param_dict['CHECKSUMHASH'])

    if verify:
        if response_dict['RESPCODE'] == '01':
            print('order successful')
            a = response_dict['ORDERID']
            b = response_dict['TXNAMOUNT']
            rid = a.replace("ShopyCart", "")
            print(rid)
            filter2 = Orders.objects.filter(order_id=rid)
            print(filter2)
            print(a, b)
            for post1 in filter2:
                post1.oid = a
                post1.amountpaid = b
                post1.paymentstatus = "PAID"
                post1.save()
            print("run agede function")
        else:
            print('order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'paymentstatus.html', {'response': response_dict, 'cust_id': cust_id})

def profile(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Login & Try Again")
        return redirect('/auth/login')
    currentuser = request.user.username
    items = Orders.objects.filter(email=currentuser)
    rid = ""
    for item in items:
        print(item.oid)
        my_id = item.oid
        rid = my_id.replace("ShopyCart", "")
        print(rid)

    order_id = None  # Initialize order_id to None
    status = None  # Initialize status to None

    if rid:  # Check if rid is not an empty string
        try:
            order_id = int(rid)
        except ValueError as e:
            print(f"Error converting rid to integer: {e}")
            # Handle the case where rid cannot be converted to an integer

    if order_id is not None:
        status = OrderUpdate.objects.filter(order_id=order_id)
    else:
        print("rid is an empty string")

    context = {"items": items, "status": status}
    return render(request, "profile.html", context)

   
    context ={"items":items,"status":status}
    # print(currentuser)
    return render(request,"profile.html",context)